# =============================================================
# NEKOVA Standard Library — Collections Module
# =============================================================
# Usage in NEKOVA:
#   use collections
#   items = make_list(1, 2, 3)
#   show list_length(items)      → 3
#   show list_get(items, 0)      → 1
#   list_add(items, 4)
#   show list_has(items, 2)      → true
#   show list_join(items, ", ")  → 1, 2, 3, 4


def load() -> dict:
    """
    Returns all collection functions to be loaded
    into the NEKOVA environment.
    """
    return {
        # Creating
        "make_list":    lambda *args: list(args),
        "make_range":   lambda start, end: list(
                            range(int(start), int(end))),

        # Reading
        "list_get":     lambda lst, i: lst[int(i)],
        "list_length":  lambda lst: len(lst),
        "list_first":   lambda lst: lst[0] if lst else None,
        "list_last":    lambda lst: lst[-1] if lst else None,
        "list_has":     lambda lst, item: item in lst,

        # Modifying
        "list_add":     lambda lst, item: lst.append(item),
        "list_remove":  lambda lst, item: lst.remove(item),
        "list_pop":     lambda lst: lst.pop(),
        "list_insert":  lambda lst, i, item: lst.insert(
                            int(i), item),
        "list_clear":   lambda lst: lst.clear(),

        # Transforming
        "list_reverse": lambda lst: list(reversed(lst)),
        "list_sort":    lambda lst: sorted(lst),
        "list_unique":  lambda lst: list(dict.fromkeys(lst)),
        "list_join":    lambda lst, sep=", ": sep.join(
                            [str(i) for i in lst]),

        # Searching
        "list_index":   lambda lst, item: lst.index(item),
        "list_count":   lambda lst, item: lst.count(item),

        # Slicing
        "list_slice":   lambda lst, start, end: lst[
                            int(start):int(end)],
    }