import sys

from type_def import *


# ========  select unit function(operator, all units)  ========


def su_all_enemy(operator_of_the_turn: Unit, units_all: list[Unit]) -> list[Unit]:
    return list(filter(lambda x: x.faction != operator_of_the_turn.faction, units_all))


def su_all_friendly(operator_of_the_turn: Unit, units_all: list[Unit]) -> list[Unit]:
    return list(filter(lambda x: x.faction == operator_of_the_turn.faction, units_all))


def _su_interact_select_one_from_candidates(candidates: list[Unit]) -> list[Unit]:
    candidate_ids = []
    [candidate_ids.append(y.unit_id) for y in candidates]

    print(f'{candidate_ids} to select, input one of those ids.')
    unit_id = int(input())
    while unit_id not in candidate_ids:
        print('input one of those ids')
        unit_id = int(input())
    for u in candidates:
        if u.unit_id == unit_id:
            return [u]


def su_one_enemy(operator_of_the_turn: Unit, units_all: list[Unit]) -> list[Unit]:
    return _su_interact_select_one_from_candidates(su_all_enemy(operator_of_the_turn, units_all))


def su_one_friendly(operator_of_the_turn: Unit, units_all: list[Unit]) -> list[Unit]:
    return _su_interact_select_one_from_candidates(su_all_friendly(operator_of_the_turn, units_all))


def su_random_one_enemy(operator_of_the_turn: Unit, units_all: list[Unit]) -> list[Unit]:
    a = su_all_enemy(operator_of_the_turn, units_all)
    random.shuffle(a)
    return [a[0]]


def su_operator_of_the_turn(operator_of_the_turn: Unit, units_all: list[Unit]) -> list[Unit]:
    return [operator_of_the_turn]


_su_dict_name_func = {
    'all_enemy': su_all_enemy,
    'one_enemy': su_one_enemy,
    'all_friendly': su_all_friendly,
    'one_friendly': su_one_friendly,
    'operator': su_operator_of_the_turn,
    'operator_of_the_turn': su_operator_of_the_turn,
    'random_one_enemy': su_random_one_enemy
}


# ========  ef_XXX effect functions  ========
# ========  ref_to_bunch_of_params | selected target units | effect params  ========
# ========  cp_XXX transform json object with json key 'XXX' to effects definitions  ========

def ef_attack(ref: BuiltInParamRef, units: list[Unit], func_param: list):
    operator = ref.unit_of_the_turn
    if func_param[4] is None:
        attack_time = func_param[3]
    else:
        attack_time = random.randint(func_param[3], func_param[4])
    for _ in range(0, attack_time):
        damage = func_param[0] + func_param[1] * operator.strength + func_param[2] * operator.intelligence
        one_hit(operator, units, damage)
        if operator.hp <= 0:
            return
        units = list(filter(lambda x: x.hp > 0, units))


def cp_attack(func_param: dict) -> Effect:
    # base_damage multiply_strength multiply_intelligence attack_times targeting
    s = str(func_param['attack_times'])
    a, b = None, None
    if s.count('-') > 0:
        a, b = s.split('-')
        a, b = int(a), int(b)
    else:
        a = int(s)
    # base_damage multiply_strength multiply_intelligence attack_at_least_x_times attack_at_most_x_times
    p = [int(func_param['base_damage']), int(func_param['multiply_strength']),
         int(func_param['multiply_intelligence']), a, b]
    return Effect(_su_dict_name_func[func_param['targeting']], ef_attack, p)


def ef_mod_buff_layer(ref: BuiltInParamRef, units: list[Unit], func_param: list):
    for target in units:
        buff, layer_num = func_param
        if target.buff.get(buff) is None or target.buff[buff] < 0:
            target.buff[buff] = 0
        target.buff[buff] += layer_num


def cp_mod_buff_layer(func_param: dict) -> Effect:
    # buff plus targeting
    buff = func_param['buff']
    plus_layer = int(func_param['plus'])
    # buff plus
    return Effect(_su_dict_name_func[func_param['targeting']], ef_mod_buff_layer, [buff, plus_layer])


def _closure_make_ef_draw_card(func_filter):
    def _c_ef_draw_card(ref: BuiltInParamRef, units: list[Unit], func_param: list):
        n = func_param[0]
        for u in units:
            draw_card(u.faction, n, func_filter)

    return _c_ef_draw_card


ef_draw_card = _closure_make_ef_draw_card(None)
ef_draw_card_attack = _closure_make_ef_draw_card(lambda _x: _x.label == 'Attack')


def cp_draw_card(func_param: dict) -> Effect:
    # amount targeting filter(optional)
    ef = ef_draw_card
    if func_param.get('filter') is not None:
        s = func_param['filter']
        if s == 'Attack':
            ef = ef_draw_card_attack
    # amount
    return Effect(_su_dict_name_func[func_param['targeting']], ef, [int(func_param['amount'])])


def ef_mod_value(ref: BuiltInParamRef, units: list[Unit], func_param: list):
    for u in units:
        k, v = func_param
        u.__dict__[k] += v


def cp_mod_value(func_param: dict) -> Effect:
    # name value targeting
    k, v = func_param['name'], func_param['value']
    # name value
    return Effect(_su_dict_name_func[func_param['targeting']], ef_mod_value, [k, v])


def ef_shuffle_deck(ref: BuiltInParamRef, units: list[Unit], func_param: list):
    for u in units:
        shuffle_deck(u.faction)


def cp_shuffle_deck(func_param: dict) -> Effect:
    return Effect(su_operator_of_the_turn, ef_shuffle_deck, None)


def ef_delayed_effect(ref: BuiltInParamRef, units: list[Unit], func_param: list):
    counter: int = func_param[0]
    es: list[Effect] = func_param[1]
    for u in units:
        u.effects_exec_later.append(DelayedEffect(counter, es))


def cp_delayed_effect(input_param: dict) -> Effect:
    # {"delayed_effect":{"counter":1,"effects":[{"draw_card":{"amount":1,"targeting":"operator","filter":"Attack"}}]}}
    counter = int(input_param['counter'])
    fp_list = input_param['effects']
    es = []
    for ikv in fp_list:
        for k, v in ikv.items():
            es.append(atom_effect_name_to_compile_function[k](v))
    return Effect(su_operator_of_the_turn, ef_delayed_effect, [counter, es])


# ========  self reference stuff  ========

_pvt_module_self = sys.modules[__name__]

atom_effect_name_to_compile_function = {}

for _pvt_init_attr in dir(_pvt_module_self):
    _pvt_init_ele = getattr(_pvt_module_self, _pvt_init_attr)
    if callable(_pvt_init_ele):
        if len(_pvt_init_attr) > 3 and _pvt_init_attr[:3] == 'cp_':
            atom_effect_name_to_compile_function[_pvt_init_attr[3:]] = _pvt_init_ele
