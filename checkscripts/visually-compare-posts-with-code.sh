#!/bin/bash
# pass both urls as args
drupal=$1
pb=$2
cd $HOME/workspaces/eclipse/dieterblog/entries
urls=()
for i in `grep CDATA *.txt | cut -d: -f1 | sort -u | xargs -n 1 -I '{}' basename '{}' .txt`
do
	echo $i
	urls+=($drupal/$i)
	urls+=($pb/$i.html)
done
luakit "${urls[@]}"
