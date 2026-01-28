# thanks snoopyjc https://stackoverflow.com/a/57246293
def oxford_comma_join(items):
    if not items:
        return ""
    elif len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return items[0] + " and " + items[1]
    else:
        return ", ".join(items[:-1]) + ", and " + items[-1]


# thanks chatgpt
def truncate_to_full_word_with_ellipsis(s, max_len):
    if len(s) <= max_len:
        return s
    else:
        s = s[: max_len - 3]  # leave room for the ellipsis
        if " " in s[-3:]:
            s = s[: s.rfind(" ")]  # truncate after last full word
        return s + "..."


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
