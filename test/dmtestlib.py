def parametrize(func, variables, *values):
    """Decorator for parametrizing tests.

    Example:
    >>> @parametrize("a,b,c", (
    ...     (1, 2, 3),
    ...     (3, 4, 7),
    ... ))
    ... def sum(a, b, c):
    ...     assert a + b == c
    """
    def wrapper():
        if isinstance(variables, str):
            variables = variables.split(",")
        variables = [v.strip() for v in variables]

        for i, vals in enumerate(values):
            if len(vals) != len(variables):
                raise ValueError("The number of variables is not equal to " + 
                                 "the number of values given for " + 
                                 "parametriziation '{}' ({} != {})".format(
                                     i, len(vals), len(variables)
                                 ))
            
            params = {}
            for j, var in enumerate(variables):
                params[var] = vals[j]
            
            return func(**params)
    return wrapper