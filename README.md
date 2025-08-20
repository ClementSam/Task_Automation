Guide développeur — Politique des entrées de Nodes

    TL;DR

        Priorité : câble > champ UI (in_default:<entrée>) > rien.

        Jamais de valeurs inventées (0, 0.0, "", False).

        Si aucune valeur : retourner None (data) ou ne rien émettre (exec).

        Booléens : parser strictement, ne jamais faire bool(value).

1) Règle d’or (uniforme sur tout le projet)

Pour chaque entrée d’un node :

    Si un câble est branché → utiliser strictement la valeur du câble (même si None).

    Sinon, utiliser la valeur du champ du node via le paramètre in_default:<nom_entree> (le moteur l’injecte déjà).

    Sinon (pas de câble et champ vide) → ne rien inventer :

        Node data (process) : renvoyer {"<sortie>": None}.

        Node exec (on_exec/start) : ne rien émettre ou passer immédiatement sans effet de bord (au cas par cas).

    ⚠️ Interdits récurrents : a or 0, text or "", bool(x), valeurs “par défaut” implicites (COM3, 115200, etc.).

2) Conventions de paramètres

    Les champs UI servant de fallback doivent écrire dans params["in_default:<nom_entree>"].
    Exemple : champ “seconds” du node Delay → in_default:seconds.

    Les noms d’entrées/sorties doivent être stables et documentés en docstring.

3) Utilitaires communs

Fichier : app/nodes/utils.py

def parse_bool_strict(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true","1","yes","y","on"}:  return True
        if s in {"false","0","no","n","off"}: return False
    return None  # indéterminé -> pas d’invention

    Optionnel (si utile dans tes nodes) :

def to_float_or_none(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None

4) Templates de nodes (à copier-coller)
4.1 Node data (ex. addition)

class Add(Node):
    """
    Entrées :
      - a (float)
      - b (float)
    Sorties :
      - sum (float | None)
    Règle : câble > in_default:a/b > None
    """
    def process(self, a=None, b=None, **_):
        if a is None or b is None:
            return {"sum": None}
        try:
            return {"sum": float(a) + float(b)}
        except Exception:
            return {"sum": None}

4.2 Node exec conditionnel (branche true/false)

from .utils import parse_bool_strict

class Branch(Node):
    """
    Entrées :
      - condition (bool)
    Sorties exec :
      - true, false
    """
    def on_exec(self, condition=None, **_):
        b = parse_bool_strict(condition)
        if b is None:
            return ([], {})  # indéterminé -> ne rien émettre
        return (["true"] if b else ["false"], {})

4.3 Node Delay (avec valeur numérique)

from .utils import to_float_or_none

class Delay(Node):
    """
    Entrées :
      - seconds (float)
    Sorties exec :
      - then
    """
    def start(self, token_id: int, seconds=None, **_):
        secs = to_float_or_none(seconds)
        if secs is None:
            # Pas d'invention -> passage immédiat
            self._scheduler.on_node_finished(self._nid, token_id, ["then"], {})
            return
        # démarrer le timer 'secs' puis émettre "then"
        ...

4.4 Node conversion (int → string)

class IntToString(Node):
    """
    Entrées :
      - value (int)
    Sorties :
      - text (str | None)
    """
    def process(self, value=None, **_):
        if value is None:
            return {"text": None}
        try:
            return {"text": str(int(value))}
        except Exception:
            return {"text": None}

4.5 Node booléen (constante)

from .utils import parse_bool_strict

class ConstBool(Node):
    """
    Champ UI :
      - value (bool/string)
    Sorties :
      - value (bool | None)
    """
    def process(self, **_):
        b = parse_bool_strict(self._params.get("value", None))
        return {"value": b}

5) Anti-patterns à bannir (revue PR)

    x or 0, x or "", x or False

    bool(x) pour interpréter une entrée (transforme None → False, "0" → True)

    Valeurs magiques implicites : ports série, baud par défaut, etc.

    Remplacer silencieusement les erreurs de parse par une valeur par défaut autre que None.

6) Politique de sortie quand valeur absente

    Data : retourner explicitement None sur la sortie concernée.

    Exec :

        Branch/conditions : ne rien émettre si indéterminé.

        Delay/temporisations : passer immédiatement (émission "then" sans attente).

        I/O (ex. série) : ne pas tenter l’action si des paramètres clés sont absents (renvoyer un état connected=False sans ouverture).

7) Check-list PR pour tout nouveau node

Les entrées respectent câble > in_default: > None.

Aucun or "", or 0, bool(x) sur les entrées.

Parsing try/except propre → None en cas d’échec.

Docstring avec Entrées/Sorties claire.

    Tests rapides (voir §8).

8) Cas de tests minimaux (exemples)

    Add : a=2 câblé, b non câblé + in_default:b=3 ⇒ sum=5.
    b câblé None ⇒ sum=None.

    AppendText : a=None (câblé), b="x" câblé, in_default:a="A" ⇒ text=None (câble > champ).

    IntToString : value=None sans champ ⇒ text=None.

    Branch : condition=None ⇒ aucune sortie ; in_default:condition="true" ⇒ sortie true.

    Delay : seconds=None ⇒ passage immédiat.

    Série : sans port/baud ⇒ pas d’ouverture, connected=False.

9) Notes d’implémentation

    Le moteur injecte déjà params["in_default:<entrée>"] quand aucun câble n’est branché : exploiter ce mécanisme, ne pas le dupliquer.

    Pour la lisibilité, préférer des fonctions utilitaires (parse_bool_strict, to_float_or_none) plutôt que des one-liners ambigus.

    Toujours logguer (niveau debug) les cas indéterminés pour faciliter le diagnostic, sans pour autant inventer de valeur.

Conclusion
Cette convention garantit des nodes prédictibles, compatibles avec l’édition UI et sûrs pour l’automatisation par Codex. En cas de doute : aucune valeur inventée — laissez None parler.

