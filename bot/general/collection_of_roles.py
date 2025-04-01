from typing import overload

from cache.cache_types import RolesLiteral
from mafia import roles
from mafia.roles import Role, ActiveRoleAtNight


@overload
def get_data_with_roles() -> dict[str, Role]: ...


@overload
def get_data_with_roles(
    role_name: RolesLiteral,
) -> Role | ActiveRoleAtNight: ...


def get_data_with_roles(
    role_name: RolesLiteral | None = None,
):
    all_roles = {
        "don": roles.Mafia(),
        "doctor": roles.Doctor(),
        "policeman": roles.Policeman(),
        "civilian": roles.Civilian(),
        "mafia": roles.MafiaAlias(),
        "traitor": roles.Traitor(),
        "killer": roles.Killer(),
        "werewolf": roles.Werewolf(),
        "forger": roles.Forger(),
        "hacker": roles.Hacker(),
        "sleeper": roles.Sleeper(),
        "agent": roles.Agent(),
        "journalist": roles.Journalist(),
        "punisher": roles.Punisher(),
        "analyst": roles.Analyst(),
        "suicide_bomber": roles.SuicideBomber(),
        "instigator": roles.Instigator(),
        "prime_minister": roles.PrimeMinister(),
        "poisoner": roles.Poisoner(),
        "bodyguard": roles.Bodyguard(),
        "masochist": roles.Masochist(),
        "lawyer": roles.Lawyer(),
        "angel_of_death": roles.AngelOfDeath(),
        "prosecutor": roles.Prosecutor(),
        "lucky_gay": roles.LuckyGay(),
        "nurse": roles.DoctorAlias(),
        "general": roles.PolicemanAlias(),
        "warden": roles.Warden(),
    }
    if role_name:
        return all_roles[role_name]
    return all_roles


BASES_ROLES = [
    "don",
    "policeman",
    "forger",
    "doctor",
    "general",
    # "doctor",
    # "doctor",
    # "traitor",
    # "masochist",
    # "analyst",
    # "killer",
    # "doctor",
    # "traitor",
    # "general",
    # "general",
]
REQUIRED_ROLES = BASES_ROLES + ["mafia"]

# TESTED 2
# bodyguard
# nurse
# doctor
# policeman
# general
# don
# mafia
# killer
# traitor
# werewolf
# civilian
# angel_of_death
# hacker
# analyst
# prime_minister
# lawyer
# instigator
# suicide_bomber
# masochist
# lucky_gay
# prosecutor
