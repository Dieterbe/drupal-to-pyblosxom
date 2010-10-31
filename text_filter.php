#!/usr/bin/env php
<?php
	$conf = array ('filter_url_length_-1' => 72);

	$text = null;
	$in = fopen('php://stdin', 'r');
	while(!feof($in)){
		$text = $text . fgets($in, 4096);
	}
	// actually for most of the interesting work (_filter_autop()) we only need that function
	// all the other deps are being dragged in for the url/email address 
	// "expansion to real html links", which btw would be more appropriate
	// as an output filter in pyblosxom (like it is in drupal). oh well..
	include_once('drupalcode/common.inc');
	include_once('drupalcode/bootstrap.inc');
	include_once('drupalcode/unicode.inc');
	include_once('drupalcode/filter.module');
	$text = _filter_autop($text); // adds <br/>'s and <p>..</p> where appropriate
	$text = _filter_url($text, -1); // expands urls/email address into real links
	echo ($text);
?>
