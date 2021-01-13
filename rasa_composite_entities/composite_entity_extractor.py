import itertools
import os
import re
import warnings

from rasa.nlu.extractors.extractor import EntityExtractor
from rasa.nlu.utils import write_json_to_file
from rasa.shared.utils.io import read_json_file

COMPOSITE_ENTITIES_FILE_NAME = "composite_entities.json"
COMPOSITE_PATTERNS_PATH_KEY = "composite_patterns_path"
ENTITY_PREFIX = "@"


class CompositeEntityExtractor(EntityExtractor):
    """A component to add composite entities to Rasa NLU. Composite patterns
    are extracted from a separate JSON definition file.
    """

    name = "CompositeEntityExtractor"
    requires = ["entities"]
    provides = ["composite_entities"]
    defaults = {COMPOSITE_PATTERNS_PATH_KEY: "composite_entity_patterns.json"}

    def __init__(self, component_config=None, composite_entities=None):
        super(CompositeEntityExtractor, self).__init__(component_config)
        self.composite_entities = composite_entities or []

    def _read_composite_entities(self):
        """Read the defined composite patterns from the train file. We have
        to manually load the file, as rasa strips our custom information.
        """
        try:
            files = [self.component_config[COMPOSITE_PATTERNS_PATH_KEY]]
        except:
            warnings.warn(
                "No composite entity patterns path set in config.yml"
            )
            return []
        composite_entities = []
        for file in files:
            try:
                file_content = read_json_file(file)
            except:
                warnings.warn(
                    f"Could not load the composite entity patterns file '{file}'."
                )
                continue
            composite_entities_in_file = file_content.get("composite_entities")
            if composite_entities_in_file:
                composite_entities.extend(composite_entities_in_file)
        if not composite_entities:
            warnings.warn(
                "CompositeEntityExtractor was added to the "
                "pipeline but no composite entities have been defined."
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
        **kwargs,
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
        entities = list(
            sorted(message.get("entities", []), key=lambda x: x["start"])
        )
        if not entities:
            return

        text_with_entity_names, index_map = self._replace_entity_values(
            message.get("text", ""), entities
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
                        "start": contained_entities[0]["start"],
                        "end": contained_entities[-1]["end"],
                        "confidence": 1.0,
                        "entity": composite_entity["name"],
                        "extractor": "CompositeEntityExtractor",
                        "value": contained_entities,
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
