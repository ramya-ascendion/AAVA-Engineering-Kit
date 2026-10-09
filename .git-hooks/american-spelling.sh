#!/bin/bash
#
# The spelling gate: American English, for code as well as prose.
#
# A house spelling rule does not hold by care. Reviewers catch the misses one at
# a time, and the misses land in files nothing else looks at — Markdown above
# all, which flake8 and pylint never see. This is what makes the rule hold.
#
# ## Configuration
#
# `KIT_SPELLING_LOCALE` in `.kit/config.env`:
#
#   american   the gate runs (the default)
#   none       the gate is skipped, and says so — a gate that is off must
#              never read as a gate that passed
#
# ## The word list is measured, not imagined
#
# Every entry below is a spelling that actually reached a commit, or is the same
# ending as one that did. It is not a general British-English dictionary and does
# not try to be. Add to it when something gets through.
#
# ## Two exemptions, because the rule must not make a document lie
#
# Quoted outside material, and names other people own. A standard whose title
# really is "Data centres", or a benchmark whose metric really is
# "Localisation", must keep the spelling its owner uses — "fixing" it would
# falsify a citation.
#
# Mark such a line with `spelling-ok` in a comment, or add the whole file to
# `spelling-exempt` beside this script (format in that file). Prefer the line
# marker: it says which line and why, where a file entry silently covers
# whatever the file grows later.
#
# **This script is exempt from itself**, by name, because the word list is the
# one place the wrong spellings have to be written down.
#
# ## What it looks at
#
# Whatever it is given, and the hook gives it the staged files. Staged rather
# than the whole tree for the reason the rest of the hook works that way: one
# badly worded file elsewhere must not block a change over here. It also means
# the backlog of files that predate the rule does not block every commit — each
# gets cleaned when it is next touched.

set -uo pipefail

# shellcheck source=.git-hooks/common.sh
source "$(dirname "$0")/common.sh"

if [ "$KIT_SPELLING_LOCALE" = "none" ]; then
    echo "    NOT RUN — KIT_SPELLING_LOCALE is none, so the spelling gate is off."
    exit 0
fi
if [ "$KIT_SPELLING_LOCALE" != "american" ]; then
    echo "    FAILED — KIT_SPELLING_LOCALE is '$KIT_SPELLING_LOCALE'; the gate knows"
    echo "    american and none. A setting nobody reads is not a setting."
    exit 1
fi

# Spellings that have actually shipped, plus the endings they belong to.
#
# **Whole words, not stems.** A stem list is what a first version had, and it
# matched "realistic" for `realis` and "Fulfillment" for `fulfil` — American
# words reported as British ones. A gate that cries wolf is a gate somebody
# switches off, so every entry here spells out its endings and is bounded at
# both ends.
#
# **The boundary is a letter test, not `\b`, and that is the second bug this
# gate had.** `\b` counts `_` as a word character, so no boundary exists inside
# a snake_case name: `\bauthorisation\b` does not match
# `sends_no_authorisation`, and `\bbehaviour\b` does not match `BEHAVIOUR_FLAG`.
# `AGENTS.md` puts identifiers under the same rule as prose, and a Python
# identifier is the one shape `\b` could not see — measured at one hit in six on
# a file of snake_case spellings. `(^|[^A-Za-z])` and `([^A-Za-z]|$)` treat `_`
# and a digit as the separators they are here.
#
# It keeps the anti-false-positive property, because the endings are still
# spelled out: "realistic" has a letter after `realis`, so the boundary refuses
# it, and "Fulfillment" has a letter after `fulfil`.
BRITISH='(^|[^A-Za-z])('\
'normalis(e|es|ed|ing|ation|ations)|'\
'(de)?serialis(e|es|ed|ing|ation|er|ers)|'\
'centre|centres|centred|centring|'\
'(un)?recognis(e|es|ed|ing|able)|'\
'judgement|judgements|'\
'organis(e|es|ed|ing|ation|ations|ational)|'\
'labelled|labelling|'\
'behaviour|behaviours|behavioural|'\
'honour|honours|honoured|honouring|honourable|'\
'acknowledgement|acknowledgements|'\
'neighbour|neighbours|neighbouring|neighbourhood|'\
'artefact|artefacts|'\
'travelling|traveller|travellers|'\
'cancelled|cancelling|'\
'licence|licences|'\
'colour|colours|coloured|colouring|colourful|'\
'realis(e|es|ed|ing|ation)|'\
'analys(e|es|ed|ing)|'\
'defence|defences|'\
'catalogue|catalogues|catalogued|'\
'prioritis(e|es|ed|ing|ation)|'\
'summaris(e|es|ed|ing)|'\
'synthesis(e|es|ed|ing)|'\
'utilis(e|es|ed|ing|ation)|'\
'minimis(e|es|ed|ing|ation)|'\
'optimis(e|es|ed|ing|ation)|'\
'apologis(e|es|ed|ing)|'\
'(un)?authoris(e|es|ed|ing|ation|ations)|'\
'programme|programmes|'\
'grey|greys|greyed|greying|'\
'modelling|modeller|'\
'signalling|'\
'fibre|fibres|'\
'fulfil|fulfils|fulfilment|'\
'enrol|enrols|enrolment|'\
'instalment|instalments|'\
'marvellous|'\
'practise|practises|practised|practising|'\
'metre|metres'\
')([^A-Za-z]|$)'


# What is wrong with one file, as `gate_over` wants it. `spelling-ok` on the line
# is the per-line exemption.
hits_in() {
    case "$1" in
        american-spelling.sh|*/american-spelling.sh) return 0 ;;
    esac
    grep -Ein "$BRITISH" "$1" 2>/dev/null | grep -v 'spelling-ok' || true
}

gate_over "$(dirname "$0")/spelling-exempt" hits_in "$@"
failed=$?

if [ "$failed" -ne 0 ]; then
    echo
    echo "    The project spells American, for code as well as prose."
    echo "    If a line is quoting someone else's words or naming something they"
    echo "    own, keep their spelling and mark the line 'spelling-ok'."
    echo "    To turn the gate off for a whole project: KIT_SPELLING_LOCALE=none"
fi

exit $failed
