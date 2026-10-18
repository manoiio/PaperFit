-- Explicit public-fixture authoring only; never used by ordinary tests or repair.
on run argv
 set filename to item 1 of argv
 tell application "Microsoft Word"
  set d to document filename
  -- Public seed: the first numbered heading follows title, abstract and SDT.
  set lp to list template of list format of text object of paragraph 6 of d
  set linked style of list level 1 of lp to name local of Word style style heading1 of d
  apply list format template (list format of text object of paragraph 6 of d) list template lp continue previous list false
  set style of text object of paragraph 6 of d to Word style style heading1 of d
  update table of contents 1 of d
  save d
  close d saving no
 end tell
end run
