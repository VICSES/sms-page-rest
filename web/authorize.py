import logging
from functools import wraps
from typing import NamedTuple, Set

from flask import request


# TODO: This should be somewhere else
def auth_failure(reason):
    return {"error":"Authorization", "detail":reason}, 403


def authorized(*predicates):
    # Multiple predicates are combined in an OR fashion
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # kwargs contains the url matched portions
            reasons = []
            post_run = []
            for p in predicates:
                error = p(**kwargs)
                if callable(error):
                    post_run.append(error)
                elif error:
                    reasons.append(error)
                else:
                    # We matched an authorization, good to go
                    return func(*args, **kwargs)

            if post_run:
                resp = func(*args, **kwargs)

                # If we proceeded on the basis of a post_run all must pass
                for p in post_run:
                    error = p(resp, **kwargs)
                    if error:
                        reasons.append(error)
                        return auth_failure(reasons)
                return resp # All passed
            else:
                return auth_failure(reasons)

        return wrapper
    return decorator


class Credentials(NamedTuple):
    member_id: int
    name: str
    unit: str
    roles: Set[str]
    permissions: Set[str]


# Based on TurboGears predicate implementation
class Predicate:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def get_credentials():
        # Spliting out mainly to help testing
        cdict = request.environ.get('authentication.credentials')
        credentials = Credentials(
            member_id = cdict['member_id'],
            name = cdict['name'],
            unit = cdict['unit'],
            roles = set(cdict['roles']),
            permissions = set(cdict['permissions'])
        )
        return credentials

    def __call__(self, *args, **kwargs):
        try:
            return self.evaluate(self.get_credentials(), kwargs)
        except Exception as e:
            self.logger.warning(e)
            return "Predicate failed to evaluate"

    def evaluate(self, credentials, url_params):
        return "Predicate not implemented, evaluate function must be provided"


class PostPredicate(Predicate):
    # Called after execution of the original request
    def __call__(self, response, **kwargs):
        (rdata, rcode) = response
        try:
            return self.evaluate(self.get_credentials(), rdata, rcode, kwargs)
        except Exception as e:
            self.logger.warning(e)
            return "Predicate failed to evaluate"

    def evaluate(self, credentials, data, code, kwargs):
        return "Predicate not implemented, evaluate function must be provided"


class post_own_unit(PostPredicate):
    failtext = "Not the member's unit"

    def evaluate(self, credentials, data, code, kwargs):
        if code != 200:
            return self.failtext
        unit = data.get('unit')
        if credentials.unit != unit:
            return self.failtext


class own_unit(Predicate):
    def evaluate(self, credentials, url_params):
        # Function is called with named parameters from the url
        # In particular we get <unit>
        unit = url_params.get('unit')
        # If we are getting a contact we might not know the unit
        # it comes from until after we have the data.
        if unit is None:
            if request.method == "GET":
                return post_own_unit()
            # FIXME: PUT editing member from other unit, changing to our
            # unit. Passes. Should fail.
            elif request.method in ("POST", "PUT"):
                unit = request.form.get('unit')
            if unit is None:
                return "URL missing unit parameter"
        if credentials.unit != unit:
            return "Not the member's unit"


class has_role(Predicate):
    def __init__(self, *roles):
        super().__init__()
        self.roles = set(roles)

    def evaluate(self, credentials, url_params):
        if credentials.roles & self.roles:
            return False # No error
        return "Required role not found"


class has_permission(Predicate):
    def __init__(self, *permissions):
        super().__init__()
        self.permissions = set(permissions)

    def evaluate(self, credentials, url_params):
        if credentials.permissions & self.permissions:
            return False # No error
        return "Required permission not found"


class post_has_all(PostPredicate):
    def __init__(self, *predicates):
        super().__init__()
        self.predicates = predicates

    def evaluate(self, credentials, data, code, kwargs):
        for p in self.predicates:
            failure = p((data,code), **kwargs)
            if failure:
                return failure


class has_all(Predicate):
    def __init__(self, *predicates):
        super().__init__()
        self.predicates = predicates

    def evaluate(self, credentials, url_params):
        post_run = []
        for p in self.predicates:
            failure = p(credentials, **url_params)
            if callable(failure):
                post_run.append(failure)
            elif failure:
                return failure
        if post_run:
            return post_has_all(*post_run)
