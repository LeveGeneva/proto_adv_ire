import random
from collections.abc import Callable

_next_unit_id = 1


def next_unit_id() -> int:
    global _next_unit_id
    _next_unit_id += 1
    return _next_unit_id


class EndTurnStub(Exception):
    pass


class Faction:
    """
    Players and their companions share the same cards and items
    """

    def __init__(self):
        self.card_hand: list[Card] = []
        self.card_draw_pile: list[Card] = []
        self.card_discard_pile: list[Card] = []
        self.card_exhaust_pile: list[Card] = []


class Unit:
    """
    For calculating damage
    """

    def __init__(self, faction: Faction, remark: str = 'enemy bot',
                 hp: int = 30, block: int = 0,
                 strength: int = 5, intelligence: int = 5, endurance: int = 5, speed: int = 5):
        self.unit_id = next_unit_id()
        self.remark = remark

        self.faction = faction

        self.block = block
        self.buff = {}
        self.speed = speed
        self.endurance = endurance
        self.intelligence = intelligence
        self.strength = strength
        self.hp = hp

        self.effects_exec_later: list[DelayedEffect] = []


class Companion(Unit):
    """
    Players' companions

    Share some properties with Unit which is for damage calculation while having its own properties like levels, names
    """

    def __init__(self, faction: Faction):
        super().__init__(faction, remark='player companion')
        self.card_kw_basic: list[Card] = []


class BuiltInParamRef:
    def __init__(self,
                 operator_of_the_turn: Unit = None,
                 units_all: list[Unit] = None):
        self.unit_of_the_turn = operator_of_the_turn
        self.units_all = units_all


class Effect:
    def __init__(
            self,
            # operator, all units -> selected units
            select_unit: Callable[[Unit, list[Unit]], list[Unit]],
            # built-in param, selected units, effect function param
            effect_func: Callable[[BuiltInParamRef, list[Unit], list], None],
            effect_param: list | None):
        self.select_unit = select_unit
        self.effect_func = effect_func
        self.effect_param = effect_param


class Card:
    def __init__(self, name: str, label: str,
                 effects: list[Effect],
                 kw_basic: bool = False, kw_innate: bool = False, kw_final: bool = False):
        self.name = name
        self.label = label
        self.effects = effects
        # causes the card to be added in hand at the beginning of turn,
        # and be removed at the end of turn if the card is never played,
        # or, end the turn if the card is played
        self.kw_basic: bool = kw_basic
        # causes the card to always start in your opening hand
        self.kw_innate: bool = kw_innate
        # end the turn if played
        self.kw_final: bool = kw_final
        # stateful keywords
        self.kw_stateful: dict[str, int] = {}


class DelayedEffect:
    def __init__(self, counter: int, card_effect_list: list[Effect]):
        self.counter = counter
        self.card_effect_list = card_effect_list


def shuffle_deck(faction: Faction):
    if len(faction.card_draw_pile) == 0:
        faction.card_draw_pile, faction.card_discard_pile = faction.card_discard_pile, faction.card_draw_pile
    random.shuffle(faction.card_draw_pile)


def draw_card(faction: Faction, n: int, func_filter):
    if len(faction.card_draw_pile) == 0:
        faction.card_draw_pile, faction.card_discard_pile = faction.card_discard_pile, faction.card_draw_pile
        random.shuffle(faction.card_draw_pile)
    if len(faction.card_draw_pile) == 0:
        return
    if func_filter is None:
        if len(faction.card_draw_pile) >= n:
            faction.card_hand.extend(faction.card_draw_pile[:n])
            faction.card_draw_pile = faction.card_draw_pile[n:]
        else:
            n = n - len(faction.card_draw_pile)
            faction.card_hand.extend(faction.card_draw_pile)
            faction.card_draw_pile.clear()

            faction.card_draw_pile, faction.card_discard_pile = faction.card_discard_pile, faction.card_draw_pile
            random.shuffle(faction.card_draw_pile)
            if n > len(faction.card_draw_pile):
                n = len(faction.card_draw_pile)
            if n > 0:
                faction.card_hand.extend(faction.card_draw_pile[:n])
                faction.card_draw_pile = faction.card_draw_pile[n:]
    else:
        t = list(filter(func_filter, faction.card_draw_pile))
        if len(t) <= 0:
            return
        if n <= len(t):
            draw = t[:n]
            faction.card_hand.extend(draw)
            [faction.card_draw_pile.remove(x) for x in draw]
        else:
            faction.card_hand.extend(t)
            [faction.card_draw_pile.remove(x) for x in t]


buff_bramble = 0
buff_endure = 1
buff_free_block = 2


def _endure(u: Unit):
    if u.hp <= 0:
        b = u.buff.get(buff_endure)
        if b is not None and b > 0:
            u.hp = 1
            u.buff[buff_endure] -= 1


def _deal_damage_considering_block(u: Unit, damage: int):
    if u.block > 0:
        damage -= u.block
        if damage <= 0:
            u.block = -damage
            return
        else:
            u.block = 0

    u.hp -= damage

    b = u.buff.get(buff_free_block)
    if b is not None and b > 0:
        u.buff[buff_free_block] -= 1


def one_hit(operator: Unit, enemies: list[Unit], damage: int):
    """

    :param operator:
    :param enemies:
    :param damage: specifically the value considering only the enhancements of the operator
    :return:
    """
    # damage being taken and backfires happen at the same time
    for enemy in enemies:
        _deal_damage_considering_block(enemy, damage)
        b = enemy.buff.get(buff_bramble)
        if b is not None and b > 0:
            _deal_damage_considering_block(operator, b)
    # death vows happen at the same time and before reborn happens
    # reborn of units happen at the same time
    _endure(operator)
    for enemy in enemies:
        _endure(enemy)
