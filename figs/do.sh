#!/bin/bash -u

python3 figs/collect_figures.py --begin 0000 --end 0999 -w figs/data/0000.json
python3 figs/collect_figures.py --begin 1000 --end 1999 -w figs/data/1000.json
python3 figs/collect_figures.py --begin 2000 --end 2999 -w figs/data/2000.json
python3 figs/collect_figures.py --begin 3000 --end 3999 -w figs/data/3000.json
python3 figs/collect_figures.py --begin 4000 --end 4999 -w figs/data/4000.json
python3 figs/collect_figures.py --begin 5000 --end 5999 -w figs/data/5000.json
python3 figs/collect_figures.py --begin 6000 --end 6999 -w figs/data/6000.json
python3 figs/collect_figures.py --begin 7000 --end 7999 -w figs/data/7000.json

python3 make_html.py 0000
python3 make_html.py 1000
python3 make_html.py 2000
python3 make_html.py 3000
python3 make_html.py 4000
python3 make_html.py 5000
python3 make_html.py 6000
python3 make_html.py 7000

python3 make_index.py
