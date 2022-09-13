class BetterDict(dict):
    def __getattr__(self, item):
        result = self[item]
        if issubclass(type(result), dict):
            return BetterDict(result)

        return result
