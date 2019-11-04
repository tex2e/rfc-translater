
# data/*/*-trans.json から html/*.html を生成するためのルール

TRANS_JSON = $(wildcard data/*/rfc*-trans.json)
TRANS_HTML = $(patsubst %.json,html/%.html,$(notdir $(subst -trans,,$(TRANS_JSON))))

all: $(TRANS_HTML)

define F
$(2): $(1)
	@#echo "$(1) ==> $(2)"
	python3 main.py --make --rfc $(patsubst html/rfc%.html,%,$(2))

endef

$(foreach x, $(TRANS_JSON),\
  $(eval $(call F,$(x),$(patsubst %.json,html/%.html,$(notdir $(subst -trans,,$(x)))))))
