# thanks snoopyjc https://stackoverflow.com/a/57246293
def oxford_comma_join(l):
    if not l:
        return ""
    elif len(l) == 1:
        return l[0]
    elif len(l) == 2:
        return l[0] + " and " + l[1]
    else:
        return ", ".join(l[:-1]) + ", and " + l[-1]
