# rasa_composite_entities

A Rasa NLU component for composite entities.

See also [my blog post](https://www.benjaminweigang.com/rasa-nlu-composite-entities/).

**Works with rasa 2.x!**

## Changelog

* 2021-01-13: Updated for Rasa 2.x. Removed old data loading logic, the only way to load patterns is now through the an external JSON file. Renamed extractor in the results from "composite" to "CompositeEntityExtractor".
* 2020-02-26: Entities are now being sorted by their `start` value before being processed. This prevents problems with other entity extractors like the duckling extractor which might change the entity order.
* 2020-01-10: The sub-entities contained in a composite entity are now found under a key named `value` instead of `contained_entities`. This change makes the output of the composite entity extractor consistent with other extractors. The major version has been bumped to mark this as a breaking change.

## Installation

```bash
$ pip install rasa_composite_entities
```

The only external dependency is Rasa NLU itself, which should be installed
anyway when you want to use this component.

After installation, the component can be added your pipeline like any other
component:

```yaml
language: en

pipeline:
- name: SpacyNLP
- name: SpacyTokenizer
- name: SpacyFeaturizer
- name: DIETClassifier
  epochs: 10
- name: EntitySynonymMapper
- name: rasa_composite_entities.CompositeEntityExtractor
```

## Usage

Create a JSON file containing the following example structure:
```json
{
 "composite_entities": [
   {
     "name": "product_with_attributes",
     "patterns": [
       "@color @product with @pattern",
       "@pattern @color @product"
     ]
   }
 ]
}
```
You can then specify the path to this variable in you pipeline like this:
```yaml
language: en

pipeline:
- name: SpacyNLP
- name: SpacyTokenizer
- name: SpacyFeaturizer
- name: DIETClassifier
  epochs: 10
- name: EntitySynonymMapper
- name: rasa_composite_entities.CompositeEntityExtractor
  composite_patterns_path: composite_entity_patterns.json
```

Using a separate file for composite entity patterns is necessary, as rasa
strips extra fields from training files. In the future, this component might
use a [custom data
importer](https://rasa.com/docs/rasa/training-data-importers) to allow giving
composite patterns directly in the training data file.

Every word starting with a "@" will be considered a placeholder for an entity
with that name. The component is agnostic to the origin of entities, you can
use anything that Rasa NLU returns as the "entity" field in its messages. This
means that you can not only use the entities defined in your common examples,
but also numerical entities from duckling etc.

Longer patterns always take precedence over shorter patterns. If a shorter
pattern matches entities that would also be matched by a longer pattern, the
shorter pattern is ignored.

Patterns are regular expressions! You can use patterns like
```
"composite_entities": [
  {
    "name": "product_with_attributes",
    "patterns": [
      "(?:@pattern\\s+)?(?:@color\\s+)?@product(?:\\s+with @[A-Z,a-z]+)?"
    ]
  }
]
```
to match different variations of entity combinations. Be aware that you may
need to properly escape your regexes to produce valid JSON files (in case of
this example, you have to escape the backslashes with another backslash).

## Explanation

Composite entities act as containers that group several entities into logical
units. Consider the following example phrase:
```
I am looking for a red shirt with stripes and checkered blue shoes.
```
Properly trained, Rasa NLU could return entities like this:
```json
"entities": [
    {
        "entity": "color",
        "start": 19,
        "end": 22,
        "confidence_entity": 0.4838929772,
        "value": "red",
        "extractor": "DIETClassifier"
    },
    {
        "entity": "product",
        "start": 23,
        "end": 28,
        "confidence_entity": 0.5812809467,
        "value": "shirt",
        "extractor": "DIETClassifier"
    },
    {
        "entity": "pattern",
        "start": 34,
        "end": 41,
        "confidence_entity": 0.7823174,
        "value": "striped",
        "extractor": "DIETClassifier",
        "processors": [
            "EntitySynonymMapper"
        ]
    },
    {
        "entity": "pattern",
        "start": 46,
        "end": 55,
        "confidence_entity": 0.8026408553,
        "value": "checkered",
        "extractor": "DIETClassifier"
    },
    {
        "entity": "color",
        "start": 56,
        "end": 60,
        "confidence_entity": 0.5482532978,
        "value": "blue",
        "extractor": "DIETClassifier"
    },
    {
        "entity": "product",
        "start": 61,
        "end": 66,
        "confidence_entity": 0.712133944,
        "value": "shoe",
        "extractor": "DIETClassifier",
        "processors": [
            "EntitySynonymMapper"
        ]
    }
]
```

It's hard to infer exactly what the user is looking for from this output alone.
Is he looking for a striped and checkered shirt? Striped and checkered shoes?
Or a striped shirt and checkered shoes?

By defining common patterns of entity combinations, we can automatically create
entity groups. If we add the composite entity patterns as in the usage example
above, the output will be changed to this:
```json
"entities": [
    {
        "start": 19,
        "end": 41,
        "confidence": 1.0,
        "entity": "product_with_attributes",
        "extractor": "CompositeEntityExtractor",
        "value": [
            {
                "entity": "color",
                "start": 19,
                "end": 22,
                "confidence_entity": 0.8646154404,
                "value": "red",
                "extractor": "DIETClassifier"
            },
            {
                "entity": "product",
                "start": 23,
                "end": 28,
                "confidence_entity": 0.5739765763,
                "value": "shirt",
                "extractor": "DIETClassifier"
            },
            {
                "entity": "pattern",
                "start": 34,
                "end": 41,
                "confidence_entity": 0.6623272896,
                "value": "striped",
                "extractor": "DIETClassifier",
                "processors": [
                    "EntitySynonymMapper"
                ]
            }
        ]
    },
    {
        "start": 46,
        "end": 66,
        "confidence": 1.0,
        "entity": "product_with_attributes",
        "extractor": "CompositeEntityExtractor",
        "value": [
            {
                "entity": "pattern",
                "start": 46,
                "end": 55,
                "confidence_entity": 0.699033916,
                "value": "checkered",
                "extractor": "DIETClassifier"
            },
            {
                "entity": "color",
                "start": 56,
                "end": 60,
                "confidence_entity": 0.8599796891,
                "value": "blue",
                "extractor": "DIETClassifier"
            },
            {
                "entity": "product",
                "start": 61,
                "end": 66,
                "confidence_entity": 0.494287014,
                "value": "shoe",
                "extractor": "DIETClassifier",
                "processors": [
                    "EntitySynonymMapper"
                ]
            }
        ]
    }
]
```

## Example

See the `example` folder for a minimal example that can be trained and tested.
To get the output from above, run:
```bash
$ cd example
$ rasa train nlu --out . --nlu train.yml --config config.yml
$ rasa run --enable-api --model .
$ curl -XPOST localhost:5005/model/parse -d '{"text": "I am looking for a red shirt with stripes and checkered blue shoes"}'
```
If you want to compare this output to the normal Rasa NLU output, just remove
the definition of the composite extractor in the config file and train again.

## License

This project is licensed under the MIT License - see the LICENSE.md file for
details.
