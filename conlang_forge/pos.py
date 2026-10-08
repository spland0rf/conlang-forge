"""Part of speech for the dictionary.

The reduced English vocabulary carries no part-of-speech data, so this is a curated lookup plus rules:

1. function-word lists (pronouns, determiners, prepositions, conjunctions, auxiliaries, numerals, interjections),
2. curated verb / adjective / adverb lists for the 2,000-word vocabulary,
3. the derivation relation in the root map (an +ADJ word is an adjective, an +AGENT word a noun ...),
4. English suffixes (-ly, -ness, -ize ...),
5. otherwise a noun.

A word can have more than one part of speech (fire: noun and verb); the first one listed is the main sense.
This is deliberately a plain table: a later review pass (human or LLM) can correct entries in one place, and the
dictionary uses whatever this module says.
"""
from __future__ import annotations

NOUN, VERB, ADJ, ADV, PREP, CONJ, PRON, DET, NUM, INTERJ, AUX = (
    "n.", "v.", "adj.", "adv.", "prep.", "conj.", "pron.", "det.", "num.", "interj.", "aux.")

NAMES = {NOUN: "noun", VERB: "verb", ADJ: "adjective", ADV: "adverb", PREP: "preposition", CONJ: "conjunction",
         PRON: "pronoun", DET: "determiner / article", NUM: "numeral", INTERJ: "interjection / greeting",
         AUX: "auxiliary verb"}


def _w(s):
    return set(s.split())


PRONOUNS = _w("""i me my mine myself you your yours yourself he him his himself she her hers herself it its itself we us
our ours ourselves they them their theirs themselves who whom whose what which whatever somebody someone something
anybody anyone anything everybody everyone everything nobody nothing none others""")
DETERMINERS = _w("a an the this that these those some any all both each every either neither few many much more most "
                 "less other another such no several enough own same plenty lot whatever")
PREPOSITIONS = _w("""to about above across after against along among around at before behind below beneath beside
besides between beyond by despite during except for from in inside into near of off on onto outside over per
past through toward towards under until upon up with within without like down out""")
CONJUNCTIONS = _w("although and as because but either if neither nor or since so than though unless until whether "
                  "while yet however therefore")
AUXILIARIES = _w("am are be is can could do may might must should will would")
NUMERALS = _w("zero one two three four five six seven eight nine ten twenty thirty hundred million dozen half "
              "first second third")
INTERJECTIONS = _w("hello goodbye hi hey oh okay yeah yes no please welcome congratulations")

VERBS = _w("""accept accuse act add admit advise affect agree aim allow announce answer apologize appeal appear appoint
approach approve argue arrest arrive ask assist attach attack attempt attend avoid ban become begin behave believe
belong bend betray bite blame bleed blow boil bore borrow bother boycott break breathe bring build burn burst bury buy
call cancel capture care carry catch cause celebrate change charge chase cheat check cheer choose claim clash climb close
collect combine come command comment communicate compare compete complete compromise concern condemn confirm confuse
congratulate conjure connect consider contain continue control cook cooperate copy correct cost count cover crash create
criticize cross crush cry cure curse cut dance deal debate decide declare decrease defeat defend define delay delegate
demand demonstrate denounce deny depend deplore deploy describe design desire destroy develop die dig disappear disarm
discover discuss dismiss dispute dive divide do drag draw dream dress drink drive drop drown dry earn ease eat elect
employ enforce enjoy enter escape establish estimate evaporate examine excite excuse execute exercise exile exist
expand expect expel explain fade fail fall feed feel fight fill find finish fit fix flee float flow fly fold follow
forge forget forgive freeze frighten gain gather get give go govern grab grind grow guarantee guard guess guide happen
harm harvest hate have heal hear help hide hit hold hope hunt hurry hurt identify ignore imagine import improve incite
include increase infect influence inform inject injure insult interfere intervene introduce invade invent invest
investigate invite involve join joke judge jump keep kick kill kiss knock know lack laugh launch lay lead leak lean
learn leave lend let lie lift like limit link list listen live load look lose love make manage march mark marry mean
measure meet melt mention miss mix mold mourn move murder need negotiate nod nominate notice obey object observe offer
open operate oppose oppress order organize oust overthrow owe paint pardon pass pause pay perform permit pick play
please plot point poison pollute postpone pour praise pray prepare present press pretend prevent process produce
promise propose protect protest prove provide pull pump punish purchase push put raid raise reach react read realize
receive recognize record recover refuse remain remember remind remove rent repair repeat reply report require research
rest restrain restrict result retire retreat return reveal revolt ride ring rise risk rob roll rub ruin rule run rush
sail save say scream search see seek seeking seem seize sell send separate serve set settle shake share shine shoot
shout shove show shrink shrug shut sigh sing sink sit slam slide slip smash smell smile snap solve speak spell spend
spill spin split spread stab stand stare start starve stay steal sting stop stretch strike struggle study succeed suffer
suggest summon supervise supply support suppose suppress surprise surrender surround survive suspect suspend swallow
swear swim swing take talk taste teach tear tell test thank think threaten throw tie tire toss touch trade train travel
treat trick trust try turn unite urge use veto violate visit vote wait wake walk want warn wash waste watch wave wear
weigh win wipe wish withdraw wonder work worry wound wrap wreck write yell zoom understand inspect hang halt possess beat sleep won""")

# verbs that are also everyday nouns (the main sense stays the verb unless the word is listed in NOUN_FIRST)
NOUN_TOO = _w("""sleep aim answer appeal attack attempt ban call care change charge claim clash comment control copy cost count
cover crash cross cry cure curse cut dance deal debate delay demand design desire dream dress drink drive drop exercise
fall fight flow fold form guard guess guide harm harvest hate help hope hunt hurry joke judge kick kiss knock lack laugh
launch lead leak limit link list load look love march mark measure mention miss mix mold move murder need nod order
pass pause pay play plot point poison praise present press process promise protest pull pump push raid record rent
repair reply report research rest result return ride ring rise risk roll rub rule rush sail search set shake share
shock shout shove show sigh slide smell smile snap spell spill spin split spread stab stand start stay step stop
stretch strike struggle study supply support surprise swing talk taste test touch trade train travel treat trick trust
turn use visit vote wait walk wash waste watch wave welcome wish work worry wound wrap wreck yell""")
NOUN_FIRST = _w("""sleep aim answer appeal attack attempt ban call care change charge claim clash comment control copy cost cover
crash cross cry cure curse cut dance deal debate delay demand design desire dream dress drink drive drop exercise fall
fight flow form guard guess guide harm harvest hope hunt joke kick kiss knock lack laugh launch lead leak limit link list
load look love march mark measure mix mold move murder need nod order pass pause pay play plot point poison praise
present press process promise protest raid record rent repair reply report research rest result return ride ring rise
risk roll rule rush sail search set shake share shout sigh slide smell smile snap spell spill spin split spread stab
start stay step stop stretch strike struggle study supply support surprise swing talk taste test touch trade train
travel treat trick trust turn use visit vote wait walk wash waste watch wave welcome wish work worry wound wrap
wreck yell""") - _w("answer call care change charge claim cost cover cut drink drive drop fall fight help hope")

ADJECTIVES = _w("""false direct kind able active afraid alive alone ancient angry asleep available average awake bad beautiful best better big
black blind blue born brave brief bright brown busy calm careful careless central certain cheap clean clear clever
cloudy cold comfortable common complete complex cool correct crazy cultural current dangerous dark dead deaf deep
dedicated democratic different difficult dirty double dry early easy economic empty entire environmental equal evil
exact excellent excited expensive extra familiar famous fast fat federal female final financial fine firm first flat
foreign former free fresh friendly full funny further gentle glad good gray great green grey guilty happy hard
healthy heavy high holy honest horrible hostile hot huge hungry illegal immediate important independent innocent
insane intelligent intense international large last late lazy left legal liberal little local lonely long loud low
lower loyal lucky main major male many medical mental middle military minor missing moderate modern moral narrow
national native natural necessary neutral new next nice noble normal old open opposite orange pale particular
perfect permanent personal physical pink pleased polite political poor popular possible pregnant pretty private
proper public pure purple quick quiet rainy rare ready real realistic reasonable recent red religious rich right
rough round royal rude sad safe same scared second secret serious severe sharp short sick significant silent silly
similar simple single slow small smooth social soft solid sorry special strange straight strong stupid successful
sudden suitable sunny sure sweet tall temporary tense terrible thick thin thirsty tidy tiny tired total traditional
tragic true ugly urgent useful usual various vicious warm weak wet white whole wide wild willing wise wonderful
wooden worse worst wrong yellow young""")
ADVERBS = _w("""how when where why far not actually ago ahead again almost already also always anymore anyway anywhere anytime away certainly down
ever everywhere forever forward hardly here immediately instead just lately later maybe mostly nearly never nowhere
now often once only perhaps probably quite rather really simply slightly so somehow sometimes somewhere soon
still then there together tonight too twice usually very well else even besides today tomorrow yesterday
especially exactly extremely finally""")
# words that are naturally both
BOTH = {"individual": (NOUN, ADJ), "commercial": (ADJ, NOUN), "plastic": (NOUN, ADJ), "material": (NOUN, ADJ), "militant": (ADJ, NOUN), "likely": (ADJ,), "today": (ADV, NOUN), "tomorrow": (ADV, NOUN), "yesterday": (ADV, NOUN), "tonight": (ADV, NOUN),
        "first": (ADJ, NUM), "second": (ADJ, NUM), "third": (ADJ, NUM), "half": (NOUN, NUM), "dozen": (NUM, NOUN),
        "alone": (ADJ, ADV), "fast": (ADJ, ADV), "late": (ADJ, ADV), "early": (ADJ, ADV), "hard": (ADJ, ADV),
        "long": (ADJ, ADV), "high": (ADJ, ADV), "low": (ADJ, ADV), "right": (ADJ, NOUN), "left": (ADJ, NOUN),
        "last": (ADJ, ADV), "next": (ADJ, ADV), "light": (NOUN, ADJ), "cool": (ADJ, VERB),
        "calm": (ADJ, VERB), "clean": (ADJ, VERB), "clear": (ADJ, VERB), "close": (VERB, ADJ), "open": (ADJ, VERB),
        "dry": (ADJ, VERB), "empty": (ADJ, VERB), "slow": (ADJ, VERB), "warm": (ADJ, VERB), "wet": (ADJ, VERB),
        "better": (ADJ, ADV), "worse": (ADJ, ADV), "best": (ADJ, ADV), "worst": (ADJ, ADV), "more": (DET, ADV),
        "most": (DET, ADV), "much": (DET, ADV), "enough": (DET, ADV), "that": (DET, CONJ), "but": (CONJ, PREP),
        "yet": (CONJ, ADV), "since": (CONJ, PREP), "until": (CONJ, PREP), "before": (PREP, CONJ), "after": (PREP, CONJ),
        "like": (PREP, VERB), "past": (PREP, NOUN), "near": (PREP, ADJ), "up": (PREP, ADV), "down": (ADV, PREP),
        "inside": (PREP, NOUN), "outside": (PREP, NOUN), "out": (ADV, PREP), "about": (PREP, ADV), "so": (CONJ, ADV),
        "as": (CONJ, PREP), "than": (CONJ, PREP), "will": (AUX, NOUN), "may": (AUX, NOUN), "can": (AUX, NOUN),
        "do": (AUX, VERB), "be": (AUX, VERB), "have": (VERB, AUX), "must": (AUX,), "need": (VERB, NOUN),
        "please": (INTERJ, VERB), "welcome": (INTERJ, VERB), "well": (ADV, NOUN), "pretty": (ADJ, ADV)}

NOUN_ALSO_VERB = _w("""plan plant store state name place block board camp cap chair film fish fire hand head house land
light line mail map model net pin pipe rock row seed shop shower sign smoke spot spring staff stage stamp steam tax
tent title top torture track trap trip tube view voice water wire cook doctor nurse guide host hammer paint knife
bottle bag box brush bundle button comb crown fence fuel gift harbor honor ink lock nail needle pocket salt shape
shelter shield skin sound spice spoon storm teacher tie tower""")

REL_POS = {"ADJ": ADJ, "ADV": ADV, "COMPAR": ADJ, "SUPERL": ADJ, "FULL": ADJ, "WITHOUT": ADJ, "ABLE": ADJ, "ORD": ADJ,
           "VERBALIZE": VERB, "CAUSE": VERB, "REVERSE": VERB, "AGAIN": VERB,
           "ABSTRACT": NOUN, "ACTION": NOUN, "RESULT": NOUN, "AGENT": NOUN, "TOOL": NOUN, "PLACE": NOUN,
           "FEMALE": NOUN, "MALE": NOUN, "YOUNG": NOUN, "COLLECTIVE": NOUN, "PLURAL": NOUN,
           "POSS": PRON, "OBJ": PRON, "SELF": PRON, "INDEP": PRON}

SUFFIX = (("ly", ADV), ("ness", NOUN), ("tion", NOUN), ("sion", NOUN), ("ment", NOUN), ("ity", NOUN),
          ("ship", NOUN), ("ism", NOUN), ("ist", NOUN), ("ize", VERB), ("ise", VERB), ("ify", VERB),
          ("ful", ADJ), ("ous", ADJ), ("less", ADJ), ("ive", ADJ), ("able", ADJ), ("ible", ADJ), ("ic", ADJ),
          ("ical", ADJ), ("al", ADJ), ("ish", ADJ), ("ary", ADJ), ("ant", ADJ))
# nouns that end like one of the suffixes above
NOUN_EXC = _w("""animal arsenal capital central cereal chapel criminal crystal festival general hospital journal
metal mineral oval pedal portal rival signal total vowel tribal canal cattle family sky ally army fly
activity ability authority community economy fantasy security city country society university liberty
facility majority minority responsibility nobility university identity quality property poverty gravity
elephant funeral immigrant mosaic traffic vegetable assistant restaurant servant ivory memory history story victory ghost library dictionary secretary anniversary vocabulary sanctuary infirmary magic music logic panic topic comic""") | _w("""relief belief ability beauty gentility
priest pilot dentist artist""")


def pos_of(cid: str, lemma: str, rel: str | None = None, in_vocab=None) -> list:
    """List of parts of speech, main one first."""
    w = lemma.lower()
    if w in BOTH:
        return list(BOTH[w])
    if w in AUXILIARIES:
        return [AUX]
    if w in PRONOUNS:
        return [PRON]
    if w in INTERJECTIONS:
        return [INTERJ]
    if w in NUMERALS:
        return [NUM]
    if w in CONJUNCTIONS and w not in PREPOSITIONS:
        return [CONJ]
    if w in PREPOSITIONS:
        return [PREP]
    if w in DETERMINERS:
        return [DET]
    if w in ADVERBS:
        return [ADV]
    if w in ADJECTIVES:
        return [ADJ]
    if w in VERBS:
        if w in NOUN_TOO:
            return [NOUN, VERB] if w in NOUN_FIRST else [VERB, NOUN]
        return [VERB]
    if rel in REL_POS:
        return [REL_POS[rel]]
    if w in NOUN_EXC:
        return [NOUN]
    for suf, p in SUFFIX:
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return [p]
    if w in NOUN_ALSO_VERB:
        return [NOUN, VERB]
    return [NOUN]
