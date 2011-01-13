#!/bin/bash
# pass both urls as args
drupal=$1
pb=$2
cd $HOME/workspaces/eclipse/dieterblog/entries/comments
urls=()
for i in `ls | sed -r 's/-[0-9]+\.[0-9]{2}\.cmt//' | sort -u`
do
	echo $i
	urls+=($drupal/$i)
	urls+=($pb/$i.html)
done
luakit "${urls[@]}"
