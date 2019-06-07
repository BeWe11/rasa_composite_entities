import itertools
import os
import re
import tempfile
import warnings

from rasa.__main__ import create_argument_parser
from rasa.data import get_core_nlu_files
from rasa.nlu.extractors import EntityExtractor
from rasa.nlu.training_data.loading import _guess_format
from rasa.nlu.utils import list_files, read_json_file, write_json_to_file

COMPOSITE_ENTITIES_FILE_NAME = "composite_entities.json"
ENTITY_PREFIX = "@"
RASA_NLU = "rasa_nlu"


class CompositeEntityExtractor(EntityExtractor):
    """A component to add composite entities to Rasa NLU. Composite patterns
    can be defined in the normal rasa JSON train data file.
    """

    name = "composite_entity_extractor"
    requires = ["entities"]
    provides = ["composite_entities"]

    def __init__(self, component_config=None, composite_entities=None):
        super(CompositeEntityExtractor, self).__init__(component_config)
        self.composite_entities = composite_entities or []

    @staticmethod
    def _get_train_files_cmd():
        """Get the raw train data by fetching the train file given in the
        command line arguments to the train script. When training the NLU model
        explicitly, the training data will be in the "nlu" argument, otherwise
        it will be in the "data" argument.
        """
        cmdline_args = create_argument_parser().parse_args()
        try:
            files = list_files(cmdline_args.nlu)
        except AttributeError:
            files = list(get_core_nlu_files(cmdline_args.data)[1])
        return [file for file in files if _guess_format(file) == RASA_NLU]

    @staticmethod
    def _get_train_files_http():
        """Get the raw train data by fetching the most recent temp train file
        that rasa has created.
        """
        # XXX: Getting the train file through the most recent temp file
        # introduces a race condition: if during training process A a new
        # training process B is started before process A reaches this component
        # (CompositeEntityExtractor), then the train file of process B will be
        # used in for composite entity extraction in process A.
        temp_dir = tempfile.gettempdir()
        train_files = [
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if f.endswith("_training_data")
        ]
        assert len(train_files) > 0, "There is no temporary train file."
        return list(sorted(train_files, key=os.path.getctime))[-1:]

    def _read_composite_entities(self):
        """Read the defined composite patterns from the train file. We have
        to manually load the file, as rasa strips our custom information.
        """
        try:
            files = self._get_train_files_cmd()
        except:
            try:
                files = self._get_train_files_http()
            except:
                warnings.warn(
                    "The CompositeEntityExtractor could not load "
                    "the train file."
                )
                return []
        composite_entities = []
        for file in files:
            file_content = read_json_file(file)
            rasa_nlu_data = file_content["rasa_nlu_data"]
            try:
                composite_entities_in_file = rasa_nlu_data[
                    "composite_entities"
                ]
            except KeyError:
                pass
            else:
                composite_entities.extend(composite_entities_in_file)
        if not composite_entities:
            warnings.warn(
                "CompositeEntityExtractor was added to the "
                "pipeline but no composite entites have been defined."
            )
        return composite_entities

    def train(self, training_data, cfg, **kwargs):
        self.composite_entities = self._read_composite_entities()

    def process(self, message, **kwargs):
        self._find_composite_entities(message)

    def persist(self, file_name, dir_name):
        if self.composite_entities:
            composite_entities_file = os.path.join(
                dir_name, COMPOSITE_ENTITIES_FILE_NAME
            )
            write_json_to_file(
                composite_entities_file,
                self.composite_entities,
                separators=(",", ": "),
            )

    @classmethod
    def load(
        cls,
        component_meta=None,
        model_dir=None,
        model_metadata=None,
        cached_component=None,
        **kwargs
    ):
        file_name = component_meta.get(
            "composite_entities_file", COMPOSITE_ENTITIES_FILE_NAME
        )
        composite_entities_file = os.path.join(model_dir, file_name)
        if os.path.isfile(composite_entities_file):
            composite_entities = read_json_file(composite_entities_file)
        else:
            composite_entities = []
            warnings.warn(
                "Failed to load composite entities"
                'file from "{}"'.format(composite_entities_file)
            )
        return cls(component_meta, composite_entities)

    @staticmethod
    def _replace_entity_values(text, entities):
        """Replace entity values with their respective entity name."""
        new_text = ""
        index_map = []
        n_entities = len(entities)
        for i in range(n_entities):
            current_entity = entities[i]

            # If there is text before the first entity, include it as well
            if i == 0:
                new_text += text[: current_entity["start"]]

            # Replace the entity value with its entity name. We store a mapping
            # from new positions to entity indices so that we can find entities
            # by refering to positions in this new string
            entity_start = len(new_text)
            new_text += ENTITY_PREFIX + current_entity["entity"]
            index_map.append((i, entity_start, len(new_text)))

            # If there is text after the last entity, include it as well
            if i == n_entities - 1:
                new_text += text[current_entity["end"] :]
            # Otherwise include the gap between this and the next entity
            else:
                next_entity = entities[i + 1]
                new_text += text[current_entity["end"] : next_entity["start"]]
        return new_text, index_map

    def _find_composite_entities(self, message):
        """Find all composite entities in a message."""
        entities = message.get("entities", [])
        if not entities:
            return

        text_with_entity_names, index_map = self._replace_entity_values(
            message.text, entities
        )

        processed_composite_entities = []
        used_entity_indices = []
        for composite_entity in self.composite_entities:
            contained_entity_indices = []
            # Sort patterns (longest pattern first) as longer patterns might
            # contain more information
            for pattern in sorted(
                composite_entity["patterns"], key=len, reverse=True
            ):
                for match in re.finditer(pattern, text_with_entity_names):
                    contained_in_match = [
                        index
                        for (index, start, end) in index_map
                        if start >= match.start() and end <= match.end()
                    ]
                    # If any entity for this match is already in the list, than
                    # this pattern is a subset of a previous (larger) pattern
                    # and we can ignore it.
                    all_indices = set(
                        itertools.chain.from_iterable(contained_entity_indices)
                    )
                    if all_indices & set(contained_in_match):
                        continue
                    contained_entity_indices.append(contained_in_match)
            if not contained_entity_indices:
                continue
            for contained_in_match in contained_entity_indices:
                contained_entities = list(
                    sorted(
                        [entities[i] for i in contained_in_match],
                        key=lambda x: x["start"],
                    )
                )
                processed_composite_entities.append(
                    {
                        "confidence": 1.0,
                        "entity": composite_entity["name"],
                        "extractor": "composite",
                        "contained_entities": contained_entities,
                    }
                )
            used_entity_indices += list(
                itertools.chain.from_iterable(contained_entity_indices)
            )

        entities = [
            entity
            for i, entity in enumerate(entities)
            if i not in used_entity_indices
        ]
        message.set(
            "entities",
            entities + processed_composite_entities,
            add_to_output=True,
        )
