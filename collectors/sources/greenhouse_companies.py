from __future__ import annotations
from .greenhouse_base import GreenhouseBoardSource


def ionq_source(**kwargs) -> GreenhouseBoardSource:
    return GreenhouseBoardSource(board_token="ionq", company="IonQ", **kwargs)


def psiquantum_source(**kwargs) -> GreenhouseBoardSource:
    # board token must match their Greenhouse subdomain token.
    # If it’s not "psiquantum", swap it once you confirm.
    return GreenhouseBoardSource(board_token="psiquantum", company="PsiQuantum", **kwargs)



