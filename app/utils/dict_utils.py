"""Dictionary utility functions."""


def deep_merge_dicts(original, incoming):
    """
    Deep merge two dictionaries. Modifies original in place.

    Args:
        original: The base dictionary that will be modified
        incoming: The dictionary to merge into original

    Returns:
        None (modifies original in place)

    Credit: Thanks Vikas https://stackoverflow.com/a/50773244
    """
    for key in incoming:
        if key in original:
            if isinstance(original[key], dict) and isinstance(incoming[key], dict):
                deep_merge_dicts(original[key], incoming[key])
            else:
                original[key] = incoming[key]
        else:
            original[key] = incoming[key]
