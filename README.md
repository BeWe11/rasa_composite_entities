# rasa_composite_entities

A Rasa NLU component for composite entities, developed to be used in the Dialogue Engine of [Dialogue Technologies](https://www.dialogue-technologies.com).

## Installation

```bash
$ pip install rasa_composite_entities
```

The only external dependency is Rasa NLU itself, which should be installed anyway when you want to use this component.

After installation, the component can be added your pipeline like any other component:

```yaml
language: "en_core_web_md"

pipeline:
- name: "nlp_spacy"
- name: "tokenizer_spacy"
- name: "intent_featurizer_spacy"
- name: "intent_entity_featurizer_regex"
- name: "ner_crf"
- name: "ner_synonyms"
- name: "intent_classifier_sklearn"
- name: "rasa_composite_entities.CompositeEntityExtractor"
```

## Usage

Simply add another entry to your training file (in JSON format) defining composite patterns:
```json
"composite_entities": [
  {
    "name": "product_with_attributes",
    "patterns": [
      "@color @product with @pattern",
      "@pattern @color @product"
    ]
  }
],
"common_examples": [
    ...
]
```
Every word starting with a "@" will be considered a placeholder for an entity with that name. The component is agnostic to the origin of entities, you can use anything that Rasa NLU returns as the "entity" field in its messages. This means that you can not only use the entities defined in your common examples, but also numerical entities from duckling etc.

Longer patterns always take precedence over shorter patterns. If a shorter pattern matches entities that would also be matched by a longer pattern, the shorter pattern is ignored.

## Explanation

Composite entities act as containers that group several entities into logical units. Consider the following example phrase:
```
I am looking for a red shirt with stripes and checkered blue shoes.
```
Properly trained, Rasa NLU could return entities like this:
```json
"entities": [
  {
    "start": 19,
    "end": 22,
    "value": "red",
    "entity": "color",
    "confidence": 0.9419322376955782,
    "extractor": "ner_crf"
  },
  {
    "start": 23,
    "end": 28,
    "value": "shirt",
    "entity": "product",
    "confidence": 0.9435936216683031,
    "extractor": "ner_crf"
  },
  {
    "start": 34,
    "end": 41,
    "value": "stripes",
    "entity": "pattern",
    "confidence": 0.9233923349716401,
    "extractor": "ner_crf"
  },
  {
    "start": 46,
    "end": 55,
    "value": "checkered",
    "entity": "pattern",
    "confidence": 0.8877627536275875,
    "extractor": "ner_crf"
  },
  {
    "start": 56,
    "end": 60,
    "value": "blue",
    "entity": "color",
    "confidence": 0.6778344517453893,
    "extractor": "ner_crf"
  },
  {
    "start": 61,
    "end": 66,
    "value": "shoes",
    "entity": "product",
    "confidence": 0.536797743231954,
    "extractor": "ner_crf"
  }
]
```

It's hard to infer exactly what the user is looking for from this output alone. Is he looking for a striped and checkered shirt? Striped and checkered shoes? Or a striped shirt and checkered shoes?

By defining common patterns of entity combinations, we can automatically create entity groups. If we add the composite entity patterns as in the usage example above, the output will be changed to this:
```json
"entities": [
  {
    "entity": "product_with_attributes",
    "type": "composite",
    "contained_entities": [
      {
        "start": 19,
        "end": 22,
        "value": "red",
        "entity": "color",
        "confidence": 0.9419322376955782,
        "extractor": "ner_crf",
        "type": "basic"
      },
      {
        "start": 23,
        "end": 28,
        "value": "shirt",
        "entity": "product",
        "confidence": 0.9435936216683031,
        "extractor": "ner_crf",
        "type": "basic"
      },
      {
        "start": 34,
        "end": 41,
        "value": "stripes",
        "entity": "pattern",
        "confidence": 0.9233923349716401,
        "extractor": "ner_crf",
        "type": "basic"
      }
    ]
  },
  {
    "entity": "product_with_attributes",
    "type": "composite",
    "contained_entities": [
      {
        "start": 46,
        "end": 55,
        "value": "checkered",
        "entity": "pattern",
        "confidence": 0.8877627536275875,
        "extractor": "ner_crf",
        "type": "basic"
      },
      {
        "start": 56,
        "end": 60,
        "value": "blue",
        "entity": "color",
        "confidence": 0.6778344517453893,
        "extractor": "ner_crf",
        "type": "basic"
      },
      {
        "start": 61,
        "end": 66,
        "value": "shoes",
        "entity": "product",
        "confidence": 0.536797743231954,
        "extractor": "ner_crf",
        "type": "basic"
      }
    ]
  }
]
```

## Example

See the `example` folder for a minimal example that can be trained and tested. To get the output from above, run:
```bash
$ python -m rasa_nlu.train --path . --data train.json --config config_with_composite.yml
$ python -m rasa_nlu.server --path . --config config_with_composite.yml
$ curl -XPOST localhost:5000/parse -d '{"q": "I am looking for a red shirt with stripes and checkered blue shoes"}'
```
If you want to compare this output to the normal Rasa NLU output, use the alternative `config_without_composite.yml` config file.

The component also works when training using the server API:
```bash
$ python -m rasa_nlu.server --path . --config config_with_composite.yml
$ curl --request POST --header 'content-type: application/x-yml' --data-binary @train_http.yml --url 'localhost:5000/train?project=test_project'
$ curl -XPOST localhost:5000/parse -d '{"q": "I am looking for a red shirt with stripes and checkered blue shoes", "project": "test_project"}'
```

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
