def dict_exists_path(obj, path, insts=[]):
    keys = path.split("/")
    try:
        for key in keys:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return False

        if insts is None or len(insts) == 0:
            return obj is not None

        for ist in insts:
            if isinstance(obj, ist): return True

        return False
    except Exception as e:
        return False


def is_error(obj):
    return dict_exists_path(obj, 'error/code')


if __name__ == "__main__":
    exist = dict_exists_path({"hello": {"world": "abcde"}}, "hello/world", str)
    print("exist = %s\n" % (exist))
