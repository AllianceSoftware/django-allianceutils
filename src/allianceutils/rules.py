import rules


def has_perm(perm, obj=None):
    """
    Creates a predicate that checks whether the user has a given permission
    Helpful for building up rules using purely predicate logic
    :param perm: permission to check
    :return: django_rules predicate
    """
    name = f'has_perm:{perm}'

    @rules.predicates.predicate(name)
    def check(user):
        return user.has_perm(perm, obj)

    return check


def has_perms(perms, obj=None):
    """
    Creates a predicate that checks whether the user has a all of a set of permissions
    Helpful for building up rules using purely predicate logic
    :param perms: permissions to check
    :return: django_rules predicate
    """
    name = 'has_perms:' + ','.join(perms)

    @rules.predicates.predicate(name)
    def check(user):
        return user.has_perms(perms, obj)

    return check


def has_any_perms(perms, obj=None):
    """
    Creates a predicate that checks whether the user has a any of a set of permissions
    Helpful for building up rules using purely predicate logic
    :param *perms: permissions to check
    :return: django_rules predicate
    """
    name = 'has_any_perms:' + ','.join(perms)

    @rules.predicates.predicate(name)
    def check(user):
        return any(user.has_perm(perm, obj) for perm in perms)

    return check
