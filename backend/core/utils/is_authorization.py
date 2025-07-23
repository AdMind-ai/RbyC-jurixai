from requests import get


def is_authorization(authorization):
    return (
        authorization != None
        and authorization != ''
        and len(authorization) > 20
    )
