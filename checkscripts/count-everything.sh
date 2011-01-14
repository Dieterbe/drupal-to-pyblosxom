#!/bin/bash
# $1 : PB blog directory
# $2 : PB blog url
dir=$1
url=$2

echo "If you don't see warnings/errors, you can assume everything is ok, except for the cases where you're asked to check something manually"
echo "Also, we obviously can't check the quality of rendered pages. do that yourself"

# count node entries on FS

entries_fs=$(ls $dir/entries/*.txt | wc -l)
echo "Entries on FS: $entries_fs (compare this with what d2py told you)"
entries_static_fs=$(ls $dir/static/*.txt | wc -l)
echo "Static entries on FS: $entries_static_fs (compare this with what d2py told you)"

# compare count of node entries from FS with wget

# we could also do a test like:
# forach entry file on FS, check if codename is listed on frontpage, and whether you can fetch $url/$codename.html
# but that might give false positives, because node names can be slightly different between PB and drupal
entries_wget=$(wget --quiet $url -O - | grep -c '<h3><a name=".*</a></h3>')
if [ "$entries_wget" = "$entries_fs" ]
then
	echo "OK, also found $entries_wget non-page node entries on the webpage.."
else
	echo "Warning: mismatch between entries on fs ($entries_fs) and found on website ($entries_wget)"
fi

# compare list of node code names from website with FS

wget --quiet $url -O - | grep '<h3><a name=".*</a></h3>' | sed 's/.*name="\([^"]*\)".*>/\1/' | sort > /tmp/d2p-check-nodes-wget
ls $dir/entries/*.txt | xargs -n 1 -I A basename A .txt | sort> /tmp/d2p-check-nodes-fs

if diff -q /tmp/d2p-check-nodes-wget /tmp/d2p-check-nodes-fs >/dev/null
then
	echo "OK, list of node identifiers from FS and wget are the same"
else
	echo "WARNING: list of node identifiers from FS differs with the wget one!. diff:"
	echo "/tmp/d2p-check-nodes-wget    <---> /tmp/d2p-check-nodes-fs"
	diff /tmp/d2p-check-nodes-wget /tmp/d2p-check-nodes-fs
fi

comments_fs=$(ls $dir/entries/comments/*.cmt | wc -l)
echo "Blog Comments on FS: $comments_fs (compare this with what d2py told you)"
comments_fs_page=$(ls $dir/entries/comments/pages/*.cmt | wc -l)
echo "Page Comments on FS: $comments_fs_page (compare this with what d2py told you)"
total_blog=0
total_pages=0
nodes_with_comments=()
pages_with_comments=()
echo "Entries with comments on FS (check this manually, if you want. this script only compares the total, which should be reasonable enough):"
echo "We'll also compare this number with what we see on the webpage"
function compare_node_comments () {
	entry=$1
	t=$2
	node=$(basename $entry .txt)
	[ "$t" = blog ] && local dir=$dir/entries/comments
	[ "$t" = page ] && local dir=$dir/entries/comments/pages
	num=$(ls $dir/$node-* 2>/dev/null | wc -l)
	if [ "$t" = blog ]
	then
		total_blog=$((total_blog+num))
		[ $num -ne 0 ] && nodes_with_comments+=($node)
	fi
	if [ "$t" = page ]
	then
		total_pages=$((total_pages+num))
		[ $num -ne 0 ] && pages_with_comments+=($node)
	fi
	echo "$node: $num  "
	# compare with webpage:
	[ "$t" = blog ] && local url=$url/$node.html
	[ "$t" = page ] && local url=$url/pages/$node.html
	num_wget=$(wget --quiet $url -O - | grep -c '<div class="blosxomComment">')
	if [ $num -eq $num_wget ]
	then
		echo "OK, same on webpage"
	else
		echo "WARNING: on webpage: $num_wget"
	fi
}
for entry in $dir/entries/*.txt
do
	compare_node_comments $entry blog
done
for entry in $dir/static/*.txt
do
	compare_node_comments $entry page
done
if [ $comments_fs -eq $total_blog ]
then
	echo "OK, sum of all blog comments with recognized nodename matches $total_blog"
else
	echo "Warning: mismatch between everything on FS matching $dir/entries/comments/*.cmt ($comments_fs) and the files in there with a recognized blog node as basename ($total_blog)"
	regex=
	for i in "${nodes_with_comments[@]}"
	do
		[ -n "$regex" ] && regex="$regex\|"
		regex="${regex}$i"
	done
	regex="^\($regex\)-1.........\.00.cmt$"
	echo "Here are the comment files without recognized node codename in them:"
	echo "These are probably for unpublished pages, if not: you just found a bug in drupal2pyblosxom!"
	ls $dir/entries/comments/ | grep -v $regex | grep -v ^pages$
fi

if [ $comments_fs_page -eq $total_pages ]
then
	echo "OK, sum of all page comments with recognized nodename matches $total_pages"
else
	echo "Warning: mismatch between everything on FS matching $dir/entries/comments/pages/*.cmt ($comments_fs_page) and the files in there with a recognized page node as basename ($total_pages)"
	regex=
	for i in "${pages_with_comments[@]}"
	do
		[ -n "$regex" ] && regex="$regex\|"
		regex="${regex}$i"
	done
	regex="^\($regex\)-1.........\.00.cmt$"
	echo "Here are the comment files without recognized node codename in them:"
	echo "These are probably for unpublished pages, if not: you just found a bug in drupal2pyblosxom!"
	ls $dir/entries/comments/pages | grep -v $regex
fi
rm /tmp/d2p*
