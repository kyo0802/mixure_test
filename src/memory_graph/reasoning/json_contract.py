import json
def parse_json(raw):
    raw = raw.strip()
    if raw.startswith('```json') and raw.endswith('```'):
        raw = raw[7:-3].strip()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Non-finite JSON number')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise ValueError('One JSON object required')
    return value
