#!/usr/bin/env python2
import optparse
import sys, os
import MySQLdb
import subprocess
import time

def start():
	p = optparse.OptionParser()
	p.add_option('--host', '-H', default="localhost")
	p.add_option('--user', '-u')
	p.add_option('--passw', '-p', default="")
	p.add_option('--db', '-d')
	p.add_option('--blog', '-b')
	p.add_option('--base', '-B', default="")
	options, arguments = p.parse_args()
	if not options.user or not options.blog or not options.db:
		p.print_help()
		sys.exit(2)
	print 'Connecting %s:%s@%s db %s and writing to %s\n' % (options.user, options.passw, options.host, options.db, options.blog)
	try:
		conn = MySQLdb.connect (host = options.host,
		     	                user = options.user,
		                        passwd = options.passw,
		                        db = options.db)
		cursor = conn.cursor()
	except Exception, e:
		sys.stderr.write ("Could not connect to database\n")
		os._exit(2)
	return cursor, options

def nodecodename (url_alias, title):
	if url_alias:
		# The url alias is usually a pretty clean starting point (at least i do my Url_aliases_like_this_and_dont_use_special_chars)
		codename = url_alias.lower()
	else:
		# first make the string lowercase and replace all useful special chars to something more appropriate:
		codename = title.lower().replace(' ','_').replace ('&','and')
		# TODO: there could still be special characters we don't want ($, ^, ...), just remove them. (accented characters should probably become non-accented) (I don't need this in my case)
	return codename

def main(cursor, options):
	print "Processing nodes..."
	try:
		# I don't have multiple revisions per node in drupal
		# I don't think pyblosxom can have different teaser per item, so we only use the full body
		# I use tagadelic with fixed tags.  we ignore tag weights and assocations between tags
		# Embedding php code ('<?php ... ?>' or '<% ... %>') like what drupal allows obviously won't work very well. Luckily I never used that feature
		# status 1 = published, 0 = not published, i haven't encountered others
		query = "SELECT node.nid, url_alias.dst, node.title, node.created, node.changed, node_revisions.body, GROUP_CONCAT(term_data.name), node.status, type \
			 FROM node \
			 LEFT JOIN url_alias ON url_alias.src = CONCAT ('node/', node.nid) \
			 JOIN node_revisions on node_revisions.nid = node.nid \
			 LEFT JOIN term_node ON term_node.nid = node.nid \
			 LEFT JOIN term_data ON term_data.tid = term_node.tid \
			 GROUP BY node.nid \
			 ORDER BY CREATED ASC"
		cursor.execute(query)
        except Exception, e:
		sys.stderr.write("Could not execute query: %s:\n%s\n" % (query, str(e)))
	for row in cursor:
		print "Processing entry: %s" % row[2]
		codename = nodecodename (row[1], row[2])
		if row[8] == 'blog':
			file_path = os.path.join(options.blog,'entries',codename+'.txt')
		else:
			file_path = os.path.join(options.blog,'static',codename+'.txt')
		if not row[7]:
			file_path += '.unpublished'
		try:
			if row[8] != 'blog':
				try:
					os.mkdir(os.path.join(options.blog,'static'))
				except OSError, e:
					pass
			file = open(file_path, 'w')
			file.write('%s\n' % row[2])
			file.write('# pubdate %s\n' % time.strftime("%Y-%m-%d", time.localtime(row[3])))
			file.write('# pubtime %s\n' % time.strftime("%H:%M:%S", time.localtime(row[3])))
			if row[6]:
				file.write('# tags %s\n' % row[6])
			if options.base:
				file.write("# guid %i at %s\n" % (row[0], options.base))
			# I've never used input format 2 (which allows almost no html) and format 1 is like format 3, but with stricter html tag allowance.
			# I just assume we use format 3, this should be good enough.
			# Perform drupalesque text processing
			p = subprocess.Popen(['./text_filter.php'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
			output = p.communicate(row[5])[0]
			file.write(output)
			file.close()
		except Exception, e:
			sys.stderr.write ("Cannot write to %s:\n%s\n" % (file_path,str(e)))
			os._exit(2)
	print "Processing comments..."
	import re
	try:
		os.mkdir(os.path.join(options.blog,'entries', 'comments'))
	except OSError, e:
		pass

	def replace_words(text, wordmap):
		for key in wordmap.keys():
			wordmap['$'+key] = wordmap[key]
			del wordmap[key]
		rc = re.compile('|'.join(map(re.escape, wordmap)))
		def translate(match):
			return wordmap[match.group(0)]
		return rc.sub(translate, text)
	try:
		f = open('pbcomment.cmt', 'r')
		comment_tpl = f.read()
		f.close()
	except Exception, e:
		sys.stderr.write("Could not load template comment file\n")
	try:
		# status 0 = published, 1 = not published, anything else: never seen
		# all my comments are in format 1
		# we assume there are no multiple comments for the same node on the same second (~same filename)
		# we also assume that you only want to keep published comments, unpublished comments are ignored
		query = "SELECT url_alias.dst, node.title, comments.cid, comments.pid, \
			 comments.nid, comments.uid, comments.subject, comments.comment, \
			 comments.hostname, comments.timestamp, comments.status, comments.name, \
			 comments.mail, comments.homepage \
			 FROM comments \
			 JOIN node on node.nid = comments.nid \
			 LEFT JOIN url_alias ON url_alias.src = CONCAT ('node/', node.nid) \
			 ORDER BY comments.nid ASC, comments.timestamp ASC"
		cursor.execute(query)
	except Exception, e:
		sys.stderr.write("Could not execute query: %s:\n%s\n" % (query, str(e)))
	namecache = {} # used to lookup filenames of earlier comments (useful for threaded comments)
	from xml.sax.saxutils import escape
	for row in cursor:
		subject = row[6].replace("\n", ' ') # not sure why, but my drupal comment subjects allowed newlines, it seems.
		commentstr = "%s:%s" % (row[1], subject)
		if row[10] >1:
			print "WARNING: Unrecognized comment status %i for comment %s" % (row[10], commentstr)
		if row[10] >0:
			continue
		print "Processing entry: %s" % commentstr
		node = nodecodename (row[0], row[1])
		comment = {}
		#comment['title'] = row[1]} # this is comments.py default behavior. but why? why store the title of the node again in the comment (and not show it..)
		comment['title'] = subject # this is what I do; it doesn't get shown usually, but at least it doesn't get lost. afaik it's the best i can do
		comment['parent'] = node # this is comments.py default behavior, but this field never seems to be used. and there is no support for anything else anyway
		# so, for the case comments.py will ever support threaded comments, this should help (key will always be set due to sorting unless db incosistency by drupal)
		if row[3]:
			comment['parent'] = namecache[row[3]]
		# all my comments are in input format 1.  since i wrote the code for input format 3 (for nodes), i won't bother to do it for format 1
		# the difference is that 3 allows html tags, whereas 1 is just a select set of tags (<a> <em> <strong> <cite> <code> <ul> <ol> <li> <dl> <dt> <dd>)
		# so you'll need to review comments manually to see if any inappropriate tags need to be left out.
		# but if you had some quality control in drupal (i.e. no spammers), i doubt this will be much work
		p = subprocess.Popen(['./text_filter.php'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		commenthtml = p.communicate(row[7])[0]
		comment['comment'] = escape(commenthtml)
		comment['author'] = row[11]
		comment['author_url'] = row[13]
		comment['author_email'] = row[12]
		comment['ip'] = row[8]
		comment['date'] = time.strftime('%a %d %b %Y', time.gmtime(row[9])) # GMT date, something like: Fri 24 Dec 2010
		comment['w3cdate'] = time.strftime ('%Y-%m-%dT%H:%M:%SZ', time.gmtime(row[9])) # GMT datetime like this: 2010-12-24T16:09:39Z
		comment['pubdate'] = "%.2f" % row[9] # unix timestamp (GMT) with centi-second resolution, like 1293206979.53 (drupal is second-resolution)
		filename = '%s-%s.cmt' % (node, comment['pubdate'])
		namecache[row[2]] = filename

		comment_str = replace_words(comment_tpl, comment)
		file_path = os.path.join(options.blog,'entries','comments',filename)
		fout = open(file_path, 'w')
		fout.write(comment_str)
		fout.close()

def report(cursor, options):
	print "\n=== Report ==="
	print "Please check if these numbers make sense!"

	print "== Drupal =="
	cursor.execute("SELECT COUNT(*) FROM node WHERE status = 1 and type = 'blog'")
	pub =  cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM node WHERE status = 1 and type = 'page'")
	pagepub = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM node WHERE status = 0 and type = 'blog'")
	unpub = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM node WHERE status = 0 and type = 'page'")
	pageunpub = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM node")
	total = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM comments WHERE status = 1")
	commentsunpub = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM comments WHERE status = 0")
	commentspub = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(*) FROM comments")
	comments_all = cursor.fetchone()[0]

	print "nodes published blog: %i"   % pub
	print "nodes unpublished blog: %i" % unpub
	print "nodes published page: %i"   % pagepub
	print "nodes unpublished page: %i" % pageunpub
	print "nodes all: %i" % total
	print "comments published: %i" % commentspub
	print "comments unpublished: %i" % commentsunpub
	print "comments all: %i" % comments_all
	total_ours = pub + unpub + pagepub + pageunpub
	if total != total_ours:
		print "WARNING: total amount of nodes (%i) doesn't match our number of recognized entries (%i)." % (total, total_ours)
		print "This means you have nodes of a status other then 0/1 or type other then blog/page, which this script does not support"
	if commentspub + commentsunpub != comments_all:
		print "WARNING: total amount of comments (%i) doesn't match our number of recognized comments (%i)." % (comments_all, commentspub + commentsunpub)
		print "This means you have comments of a status other then 0/1, which this script does not support"

	print "== Pyblosxom =="
	import glob
	pbpub         = len(glob.glob1(os.path.join(options.blog,'entries'),"*.txt"))
	pbunpub       = len(glob.glob1(os.path.join(options.blog,'entries'),"*.txt.unpublished"))
	pbstaticpub   = len(glob.glob1(os.path.join(options.blog,'static'),"*.txt"))
	pbstaticunpub = len(glob.glob1(os.path.join(options.blog,'static'),"*.txt.unpublished"))
	pbcomments    = len(glob.glob1(os.path.join(options.blog,'entries', 'comments'),"*.cmt"))
	print "entries published: %i"   % pbpub
	print "entries unpublished: %i" % pbunpub
	print "statics published: %i"   % pbstaticpub
	print "statics unpublished: %i" % pbstaticunpub
	print "entries+statics all: %i" % (pbpub + pbunpub + pbstaticpub + pbstaticunpub)
	print "comments: %i"            % pbcomments
	if pbcomments != commentspub:
		print "WARNING: pb export misses some comments"
	if pbpub != pub:
		print "WARNING: pb export misses some published blog entries"
	if pbunpub != unpub:
		print "WARNING: pb export misses some unpublished blog entries"
	if pbstaticpub != pagepub:
		print "WARNING: pb export misses some published static pages"
	if pbstaticunpub != pageunpub:
		print "WARNING: pb export misses some unpublished static pages"


if __name__ == '__main__':
	try:
		cursor, options = start()
		main(cursor, options)
		report(cursor, options)
	except Exception, e:
		import traceback
		sys.stderr.write ("%s\n" % str(e))
		traceback.print_exc()
		os._exit(1)
