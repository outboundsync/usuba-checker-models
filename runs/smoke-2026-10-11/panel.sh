for m in "$@"; do n=$(echo $m | sed 's#.*/##'); python3 gen_or.py $m gen_$n.jsonl > or_$n.log 2>&1; echo "$m $(tail -1 or_$n.log)" >> panel_costs.txt; done
