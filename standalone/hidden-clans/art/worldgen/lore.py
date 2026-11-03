"""The world's history, told by the generator: names the lands (the old realms) and gives every
place a line of its own story, the same every run for a seed. The history itself is in
planning/WORLD_LORE_2026-10-27.md; this file only fills in each place's part of it.

Nobody lives in the world now except the players, beasts and monsters, and the kobolds and
goblins in their caves (owner, 10-27). The cities and holds are the ruins of the old realms.
"""
import math

import numpy as np

from heartland import *  # noqa: F401,F403
from noise import fbm

WORLD_NAME = None   # no names (owner, 10-27): players name what they claim
PEOPLE = {"human": "humans", "dwarf": "dwarves", "elf": "night elves", "lizard": "lizardmen", "frog": "frogmen",
          "orc": "orcs", "goblin": "goblins", "kobold": "kobolds"}
LAND_A = ["Kel", "Ost", "Bran", "Ith", "Vor", "Mael", "Dun", "Sar", "Thal", "Eld", "Hal", "Cor", "Wyr", "Ul",
          "Fen", "Gar", "Ash", "Brin", "Lor", "Ves"]
LAND_B = ["mar", "wen", "ra", "eth", "an", "is", "or", "ul", "ven", "ia", "and", "ost"]
LAND_KIND = {K_FOREST: "Weald", K_JUNGLE: "Tangle", K_MARSH: "Fens", K_GRASS: "March", K_DESERT: "Sands",
             K_MESA: "Redlands", K_SNOW: "Fells", K_TUNDRA: "Fells", K_ROCK: "Crags", K_ASH: "Cinders",
             K_SAND: "Coast", K_SHORE: "Coast"}
ONE = {"human": "human", "dwarf": "dwarf", "elf": "night elf", "lizard": "lizardman", "frog": "frogman",
       "orc": "orc", "goblin": "goblin", "kobold": "kobold"}
DUNGEON_NAME = {"crypt": "Crypt of {a}", "barrow": "{a} Barrow", "tomb": "Tomb of {a}", "cave": "{a} Caves",
                "ice cave": "{a} Ice Caves", "mushroom cavern": "{a} Mushroom Hollow", "dragon lair": "{a} Peak",
                "hellgate": "The Gate at {a}", "kobold warren": "{a} Kobold Warren", "goblin cave": "{a} Goblin Hole",
                "deep hall": "Stair of {a}"}
RUIN_KINDS = ["watchtower", "shrine", "battlefield", "standing stones", "waystation", "bridge fort"]


def _rng(seed, i, salt):
    return np.random.default_rng((seed * 1000003 + i * 7919 + salt * 104729) & 0xFFFFFFFF)


def land_name(rng, biome):
    a = LAND_A[rng.integers(len(LAND_A))]
    b = LAND_B[rng.integers(len(LAND_B))]
    return "%s%s %s" % (a, b, LAND_KIND.get(int(biome), "March"))


def lands(w):
    """The old realms: each fallen city was a realm's seat; its land is the ground nearest it
    (with a wobble, so borders follow no straight line). Far islands are the Wilds."""
    G = w.h.shape[0]
    seats = [p for p in w.places if p["kind"] in ("fallen_city", "heartland")]
    wob = fbm(w.cwx, w.cwy, w.seed + 90, 1800, 200) * 2600
    best = np.full((G, G), np.inf)
    owner = np.full((G, G), -1, np.int16)
    for i, p in enumerate(seats):
        d = np.hypot(w.cwx - p["x"], w.cwy - p["y"]) + wob * (1 if i % 2 else -1) * 0.5
        closer = d < best
        best[closer] = d[closer]
        owner[closer] = i
    owner[(w.h < 0) | (best > 3600)] = -1
    w.land_of = owner
    w.lands = []
    for i, p in enumerate(seats):
        cells = np.argwhere(owner == i)
        if p["kind"] == "heartland":
            name = "The Heartland"
        else:
            # named for its most common land, leaving out bare rock and beaches
            b = w.biome[cells[:, 0], cells[:, 1]] if len(cells) else np.array([p["biome"]])
            b = b[~np.isin(b, [K_ROCK, K_SAND, K_SHORE, K_WATER, K_DEEP])]
            major = np.bincount(b, minlength=NKINDS).argmax() if len(b) else p["biome"]
            name = land_name(_rng(w.seed, p["id"], 1), major)
        cy, cx = cells.mean(0) if len(cells) else (p["y"] / 16, p["x"] / 16)
        w.lands.append({"name": name, "seat": p["id"], "people": p.get("race"), "cx": float((cx + 0.5) * 16),
                        "cy": float((cy + 0.5) * 16), "regions": int(round(len(cells) / 256))})
        p["land"] = name
    for p in w.places:
        if "land" not in p:
            o = owner[min(G - 1, int(p["y"] // 16)), min(G - 1, int(p["x"] // 16))]
            p["land"] = w.lands[o]["name"] if o >= 0 else "the Wilds"


def _nearest(w, p, pred, limit):
    best = None
    for q in w.places:
        if q is p or not pred(q):
            continue
        d = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
        if d < limit and (best is None or d < best[0]):
            best = (d, q)
    return best[1] if best else None


def stories(w):
    """Every place's line of history, with no names in it (owner, 10-27: "i kind of want no names i want
    people to conquer and claim the land make kingdoms"). A place is called what it is; players name
    what they take."""
    gates = sum(1 for p in w.places if p.get("type") == "hellgate")
    w.gate_count = gates
    for p in w.places:
        r = _rng(w.seed, p["id"], 2)
        k = p["kind"]
        folk = PEOPLE.get(p.get("race"), "old peoples")
        one = ONE.get(p.get("race"), "old")
        an = "an" if one[0] in "aeiou" else "a"
        pick = lambda xs: xs[int(r.integers(len(xs)))]
        if k == "heartland":
            p["name"] = "The Old Heartland"
            p["story"] = ("The one vale the gates never reached, ringed by mountains. The last of every people "
                          "gathered here after the Breaking; from here the companies ride out under their banners.")
        elif k == "fallen_city":
            p["name"] = "fallen city"
            gate = _nearest(w, p, lambda q: q.get("type") == "hellgate", 2600)
            lair = _nearest(w, p, lambda q: q.get("type") == "dragon lair", 2200)
            if gate:
                cause = "when a hellgate burst open a day's march away"
            elif lair:
                cause = "when a dragon came down from the peaks for its treasury"
            else:
                cause = pick(["when its own deep mines broke through into the fire below",
                              "to the dead that walked up out of its crypts",
                              "to fire and famine in the winter after the gates opened"])
            now = pick(["Its walls still stand in places, and %s den in its halls." % _beast_near(w, p),
                        "The keep is still whole, and on some nights a light burns in it.",
                        "Nothing has lived there for three hundred years but crows.",
                        "Its treasury was never found."])
            p["story"] = "A fallen city, the greatest the %s ever raised, seat of a realm whose name is forgotten. " \
                         "It fell %s. %s" % (folk, cause, now)
        elif k == "hold":
            p["name"] = "abandoned hold"
            dv = _nearest(w, p, lambda q: q["kind"] == "delving", 1200)
            if p.get("port"):
                trade = "a harbour on the old sea lanes"
            elif dv:
                trade = "rich once on the %s of a delving nearby" % dv["ore"]
            else:
                trade = pick(["on the old road", "on the edge of the wild", "at a river crossing"])
            fate = pick(["Its people fled to the Heartland in the last winter of the Breaking.",
                         "It was burned and never rebuilt.",
                         "Its people went down into the cellars to hide and did not come up again.",
                         "It held for a generation after the Breaking, then the wells failed.",
                         "Its walls are good; it only wants people."])
            p["story"] = "An abandoned %s hold, %s. %s" % (one, trade, fate)
        elif k == "delving":
            p["name"] = "old delving"
            p["story"] = "An old delving, dug for %s and left when %s. The ore is still there." % (
                p["ore"], pick(["the deepest shafts broke into fire", "the lower galleries flooded",
                                "something came up the shafts", "the realm above it fell"]))
        elif k == "lair":
            p["name"] = "den of " + p["beast"].replace("a sand king", "a sand king")
            p["story"] = "A den of %s. %s" % (p["beast"], pick(["Bones of travellers round the mouth.",
                                                              "Fresh tracks every morning.",
                                                              "Hunters from the old holds never came back from it.",
                                                              "The ground is trampled bare for a stone's throw."]))
        elif k == "dungeon":
            t = p["type"]
            p["name"] = t
            if t in ("crypt", "barrow", "tomb"):
                s = "where the lords of a forgotten realm were laid. The dead in it do not rest"
            elif t == "dragon lair":
                s = "a dragon took this peak after the Breaking and sleeps on the gold of a fallen city"
            elif t == "hellgate":
                s = "one of the %d gates that opened on the Night of Open Gates. Demons still climb out of it" % gates
            elif t == "kobold warren":
                s = "kobolds live here as they did before the Breaking: they hid deep and outlasted everyone"
            elif t == "goblin cave":
                s = "a goblin band holds this cave and raids whatever passes on the old road"
            elif t == "deep hall":
                s = "stairs down to the halls of the svartalfar and the mind-eaters, who never came up"
            elif t == "mushroom cavern":
                s = "a cavern of giant mushrooms; cave spiders and tower caps live among them"
            elif t == "ice cave":
                s = "a cave under the ice, running down into the Underhalls"
            else:
                s = "a cave running down into the Underhalls"
            p["story"] = s[0].upper() + s[1:] + "."
        elif k == "ruin":
            rk = RUIN_KINDS[int(r.integers(len(RUIN_KINDS)))]
            p["ruin"] = rk
            p["name"] = rk + " ruins"
            p["story"] = "A fallen %s of a forgotten realm." % rk
        elif k == "underhall":
            p["name"] = "underhalls"
            p["story"] = ("Underhalls: before the peoples climbed out under their banners, %s %s lived here, under "
                          "the mountain. The halls are empty now, and the cave folk use them." % (an, one) if False else
                          "Underhalls: before the peoples climbed out under their banners, the %s lived here, under "
                          "the mountain. The halls are empty now, and the cave folk use them." % folk)
        elif k == "demon keep":
            p["name"] = "demon keep"
            p["story"] = ("A keep the demons raised in the Deep beside a hellgate's shaft, ringed in fire. "
                          "Whoever holds it holds the gate from below.")
        elif k == "the wound":
            p["name"] = "The Wound"
            p["story"] = ("The Wound: the place the shafts broke through on the Night of Open Gates, a pit in a sea "
                          "of fire at the heart of the Deep. The old thing that woke sleeps under it.")
        elif k == "sky island":
            if p["great"]:
                p["name"] = "The Sky Isle"
                p["story"] = ("The Sky Isle: on the Night of Open Gates the Deep heaved and tore a hill out of the "
                              "earth, lake and all, and threw it into the sky. It never came down. Its lake pours off "
                              "the edge as the Great Falls, straight down into the sea. Skystone grows in its rim.")
            else:
                p["name"] = "skyrock"
                p["story"] = "A skyrock: a shard of land torn up in the Breaking, still floating. Skystone in its rim."
        elif k == "falls":
            p["name"] = "The Great Falls"
            p["story"] = ("The Great Falls: the lake of the Sky Isle pours over its edge and falls from the sky into "
                          "the sea. Sailors see the mist for a day before they see the isle.")


def _beast_near(w, p):
    q = _nearest(w, p, lambda q: q["kind"] == "lair", 3000)
    return q["beast"] if q else "wolves"


def _lair_name(p, r):
    base = {"wolves": "Wolf", "giant spiders": "Spider", "death beetles": "Beetle", "a sand king": "Sand King",
            "demons": "Demon", "ratmen": "Ratmen", "giant moles": "Mole"}.get(p["beast"], "Beast")
    place = ["Hollow", "Den", "Pit", "Holes", "Warren", "Rocks", "Thicket", "Mound"][int(r.integers(8))]
    return "%s %s" % (base, place)
