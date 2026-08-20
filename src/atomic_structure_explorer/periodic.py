from __future__ import annotations

from .models import ElectronConfiguration, Element, Subshell


_ELEMENT_ROWS = [
    ("H", "Hydrogen", 1, 1), ("He", "Helium", 1, 18),
    ("Li", "Lithium", 2, 1), ("Be", "Beryllium", 2, 2), ("B", "Boron", 2, 13),
    ("C", "Carbon", 2, 14), ("N", "Nitrogen", 2, 15), ("O", "Oxygen", 2, 16),
    ("F", "Fluorine", 2, 17), ("Ne", "Neon", 2, 18),
    ("Na", "Sodium", 3, 1), ("Mg", "Magnesium", 3, 2), ("Al", "Aluminium", 3, 13),
    ("Si", "Silicon", 3, 14), ("P", "Phosphorus", 3, 15), ("S", "Sulfur", 3, 16),
    ("Cl", "Chlorine", 3, 17), ("Ar", "Argon", 3, 18),
    ("K", "Potassium", 4, 1), ("Ca", "Calcium", 4, 2), ("Sc", "Scandium", 4, 3),
    ("Ti", "Titanium", 4, 4), ("V", "Vanadium", 4, 5), ("Cr", "Chromium", 4, 6),
    ("Mn", "Manganese", 4, 7), ("Fe", "Iron", 4, 8), ("Co", "Cobalt", 4, 9),
    ("Ni", "Nickel", 4, 10), ("Cu", "Copper", 4, 11), ("Zn", "Zinc", 4, 12),
    ("Ga", "Gallium", 4, 13), ("Ge", "Germanium", 4, 14), ("As", "Arsenic", 4, 15),
    ("Se", "Selenium", 4, 16), ("Br", "Bromine", 4, 17), ("Kr", "Krypton", 4, 18),
    ("Rb", "Rubidium", 5, 1), ("Sr", "Strontium", 5, 2), ("Y", "Yttrium", 5, 3),
    ("Zr", "Zirconium", 5, 4), ("Nb", "Niobium", 5, 5), ("Mo", "Molybdenum", 5, 6),
    ("Tc", "Technetium", 5, 7), ("Ru", "Ruthenium", 5, 8), ("Rh", "Rhodium", 5, 9),
    ("Pd", "Palladium", 5, 10), ("Ag", "Silver", 5, 11), ("Cd", "Cadmium", 5, 12),
    ("In", "Indium", 5, 13), ("Sn", "Tin", 5, 14), ("Sb", "Antimony", 5, 15),
    ("Te", "Tellurium", 5, 16), ("I", "Iodine", 5, 17), ("Xe", "Xenon", 5, 18),
    ("Cs", "Caesium", 6, 1), ("Ba", "Barium", 6, 2),
    ("La", "Lanthanum", 6, 3), ("Ce", "Cerium", 6, 3), ("Pr", "Praseodymium", 6, 3),
    ("Nd", "Neodymium", 6, 3), ("Pm", "Promethium", 6, 3), ("Sm", "Samarium", 6, 3),
    ("Eu", "Europium", 6, 3), ("Gd", "Gadolinium", 6, 3), ("Tb", "Terbium", 6, 3),
    ("Dy", "Dysprosium", 6, 3), ("Ho", "Holmium", 6, 3), ("Er", "Erbium", 6, 3),
    ("Tm", "Thulium", 6, 3), ("Yb", "Ytterbium", 6, 3), ("Lu", "Lutetium", 6, 3),
    ("Hf", "Hafnium", 6, 4), ("Ta", "Tantalum", 6, 5), ("W", "Tungsten", 6, 6),
    ("Re", "Rhenium", 6, 7), ("Os", "Osmium", 6, 8), ("Ir", "Iridium", 6, 9),
    ("Pt", "Platinum", 6, 10), ("Au", "Gold", 6, 11), ("Hg", "Mercury", 6, 12),
    ("Tl", "Thallium", 6, 13), ("Pb", "Lead", 6, 14), ("Bi", "Bismuth", 6, 15),
    ("Po", "Polonium", 6, 16), ("At", "Astatine", 6, 17), ("Rn", "Radon", 6, 18),
    ("Fr", "Francium", 7, 1), ("Ra", "Radium", 7, 2),
    ("Ac", "Actinium", 7, 3), ("Th", "Thorium", 7, 3), ("Pa", "Protactinium", 7, 3),
    ("U", "Uranium", 7, 3), ("Np", "Neptunium", 7, 3), ("Pu", "Plutonium", 7, 3),
    ("Am", "Americium", 7, 3), ("Cm", "Curium", 7, 3), ("Bk", "Berkelium", 7, 3),
    ("Cf", "Californium", 7, 3), ("Es", "Einsteinium", 7, 3), ("Fm", "Fermium", 7, 3),
    ("Md", "Mendelevium", 7, 3), ("No", "Nobelium", 7, 3), ("Lr", "Lawrencium", 7, 3),
    ("Rf", "Rutherfordium", 7, 4), ("Db", "Dubnium", 7, 5), ("Sg", "Seaborgium", 7, 6),
    ("Bh", "Bohrium", 7, 7), ("Hs", "Hassium", 7, 8), ("Mt", "Meitnerium", 7, 9),
    ("Ds", "Darmstadtium", 7, 10), ("Rg", "Roentgenium", 7, 11), ("Cn", "Copernicium", 7, 12),
    ("Nh", "Nihonium", 7, 13), ("Fl", "Flerovium", 7, 14), ("Mc", "Moscovium", 7, 15),
    ("Lv", "Livermorium", 7, 16), ("Ts", "Tennessine", 7, 17), ("Og", "Oganesson", 7, 18),
]


def _make_elements() -> tuple[Element, ...]:
    result: list[Element] = []
    lanthanide_column = 4
    actinide_column = 4
    for z, (symbol, name, period, group) in enumerate(_ELEMENT_ROWS, start=1):
        if 58 <= z <= 71:
            row, column = 8, lanthanide_column
            lanthanide_column += 1
        elif 90 <= z <= 103:
            row, column = 9, actinide_column
            actinide_column += 1
        else:
            row, column = period, group
        result.append(Element(z, symbol, name, period, group, row, column))
    return tuple(result)


ELEMENTS = _make_elements()
ELEMENT_BY_Z = {e.atomic_number: e for e in ELEMENTS}
ELEMENT_BY_SYMBOL = {e.symbol: e for e in ELEMENTS}

AUFBAU_ORDER = (
    (1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (3, 2), (4, 1),
    (5, 0), (4, 2), (5, 1), (6, 0), (4, 3), (5, 2), (6, 1), (7, 0),
    (5, 3), (6, 2), (7, 1),
)


def aufbau_configuration(electrons: int) -> ElectronConfiguration:
    remaining = electrons
    filled: list[Subshell] = []
    for n, l in AUFBAU_ORDER:
        if remaining <= 0:
            break
        occupation = min(remaining, 2 * (2 * l + 1))
        filled.append(Subshell(n, l, occupation))
        remaining -= occupation
    if remaining:
        raise ValueError(f"Aufbau order is incomplete for {electrons} electrons")
    return ElectronConfiguration(tuple(filled), "Madelung prediction")


# Adjustments to the Madelung filling used only for the separately labelled
# accepted comparison. The numerical model never silently substitutes these.
_ACCEPTED_ADJUSTMENTS: dict[int, dict[tuple[int, int], int]] = {
    24: {(4, 0): 1, (3, 2): 5}, 29: {(4, 0): 1, (3, 2): 10},
    41: {(5, 0): 1, (4, 2): 4}, 42: {(5, 0): 1, (4, 2): 5},
    44: {(5, 0): 1, (4, 2): 7}, 45: {(5, 0): 1, (4, 2): 8},
    46: {(5, 0): 0, (4, 2): 10}, 47: {(5, 0): 1, (4, 2): 10},
    57: {(4, 3): 0, (5, 2): 1, (6, 0): 2},
    58: {(4, 3): 1, (5, 2): 1, (6, 0): 2},
    64: {(4, 3): 7, (5, 2): 1, (6, 0): 2},
    78: {(6, 0): 1, (5, 2): 9}, 79: {(6, 0): 1, (5, 2): 10},
    89: {(5, 3): 0, (6, 2): 1, (7, 0): 2},
    90: {(5, 3): 0, (6, 2): 2, (7, 0): 2},
    91: {(5, 3): 2, (6, 2): 1, (7, 0): 2},
    92: {(5, 3): 3, (6, 2): 1, (7, 0): 2},
    93: {(5, 3): 4, (6, 2): 1, (7, 0): 2},
    96: {(5, 3): 7, (6, 2): 1, (7, 0): 2},
    103: {(6, 2): 0, (7, 1): 1, (7, 0): 2},
}


def accepted_configuration(atomic_number: int) -> ElectronConfiguration:
    predicted = aufbau_configuration(atomic_number)
    adjustments = _ACCEPTED_ADJUSTMENTS.get(atomic_number)
    if not adjustments:
        return ElectronConfiguration(predicted.subshells, "accepted reference")
    occupations = {(s.n, s.l): s.occupation for s in predicted.subshells}
    occupations.update(adjustments)
    ordered: list[Subshell] = []
    for n, l in AUFBAU_ORDER:
        occ = occupations.get((n, l), 0)
        if occ:
            ordered.append(Subshell(n, l, occ))
    return ElectronConfiguration(tuple(ordered), "accepted reference")


_NOBLE_CORES = ((86, "Rn"), (54, "Xe"), (36, "Kr"), (18, "Ar"), (10, "Ne"), (2, "He"))


def format_configuration(configuration: ElectronConfiguration, shorthand: bool = True) -> str:
    prefix = ""
    subshells = list(configuration.subshells)
    if shorthand:
        for core_z, core_symbol in _NOBLE_CORES:
            if configuration.electron_count > core_z:
                core = accepted_configuration(core_z).subshells
                if tuple(subshells[: len(core)]) == core:
                    prefix = f"[{core_symbol}] "
                    subshells = subshells[len(core):]
                    break
    return prefix + " ".join(s.label + (str(s.occupation) if s.occupation != 1 else "") for s in subshells)


def valence_count(configuration: ElectronConfiguration) -> int:
    if not configuration.subshells:
        return 0
    outer_n = max(s.n for s in configuration.subshells)
    return sum(s.occupation for s in configuration.subshells if s.n == outer_n)
