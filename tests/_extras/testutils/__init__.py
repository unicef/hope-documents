import logging

logger = logging.getLogger(__name__)


def flatten(nested_structure):
    """
    Recursively flattens a list or tuple of any depth.
    """
    flat_list = []
    for item in nested_structure:
        # If the item is a list or tuple, extend the list with its flattened version
        if isinstance(item, (list, tuple)):
            flat_list.extend(flatten(item))
        # Otherwise, just append the item
        else:
            flat_list.append(item)
    return flat_list
