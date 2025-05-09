#!/usr/local/bin/perl
# Create, update or delete a record

require './virtual-server-lib.pl';
&ReadParse();
&licence_status();
&error_setup($text{'record_err'});
$d = &get_domain($in{'dom'});
$d || &error($text{'edit_egone'});
&can_edit_domain($d) || &error($text{'edit_ecannot'});
&can_edit_records($d) || &error($text{'records_ecannot'});
&copy_alias_records($d) && &error($text{'records_ecannot2'});
&require_bind();
&pre_records_change($d);
($recs, $file) = &get_domain_dns_records_and_file($d);
$file || &error($recs);

if (!$in{'type'}) {
	# Get the record
	($r) = grep { $_->{'id'} eq $in{'id'} } @$recs;
	$r || &error($text{'record_egone'});
	}
else {
	# Creating a new one
	if ($in{'type'} eq '$ttl') {
		$r = { 'defttl' => '1h' };	# defttl gets set later
		}
	else {
		$r = { 'type' => $in{'type'},
		       'class' => 'IN' };
		}
	}

&obtain_lock_dns($d);
if ($in{'delete'}) {
	# Just delete it
	&can_delete_record($d, $r) || &error($text{'record_edelete'});
	&delete_dns_record($recs, $file, $r);
	}
elsif ($r->{'defttl'}) {
	# Validate and save default TTL
	$in{'defttl'} =~ /^\d+$/ && $in{'defttl'} > 0 ||
		&error($text{'record_ettl'});
	$in{'defttl_units'} =~ /^[a-z]$/i ||
		&error($text{'record_ettlunits'});
	$r->{'defttl'} = $in{'defttl'}.$in{'defttl_units'};
	if (&supports_dns_comments($d)) {
		$r->{'comment'} = $in{'comment'};
		}

	# Create or update record
	if ($in{'type'}) {
		# Create the TTL, renumbering others up so that bumping the SOA
		# modifies the correct line
		&create_dns_record($recs, $file, $r);
		}
	else {
		# Just update it
		&modify_dns_record($recs, $file, $r);
		}

	}
else {
	# Validate and save record
	($t) = grep { $_->{'type'} eq $r->{'type'} } &list_dns_record_types($d);
	&can_edit_record($d, $r) && $t || &error($text{'record_eedit'});
	if ($in{'type'} || $r->{'name'} ne $d->{'dom'}.".") {
		# Validate name
		if ($in{'name_def'}) {
			$r->{'name'} = $d->{'dom'}.".";
			}
		else {
			$in{'name'} =~ /^[a-z0-9\.\_\-]+$/i ||
			    $in{'name'} eq '*' ||
			    $in{'name'} =~ /^\*\.[a-z0-9\.\_\-]+$/i ||
				&error($text{'record_ename'});
			($in{'name'} =~ /^\./ || $in{'name'} =~ /\.$/) &&
				&error($text{'record_enamedot'});
			$in{'name'} =~ /(^|\.)$d->{'dom'}$/i &&
				&error($text{'record_enamedom'});
			$r->{'name'} = $in{'name'}.".".$d->{'dom'}.".";
			}

		# Add SRV record components
		if ($r->{'type'} eq 'SRV') {
			$in{'sservice'} =~ /^[a-z0-9\.\_\-]+$/i ||
				&error($text{'record_esservice'});
			$in{'sproto'} =~ /^[a-z0-9\.\_\-]+$/i ||
				&error($text{'record_esproto'});
			$r->{'name'} = '_'.$in{'sservice'}.'._'.$in{'sproto'}.
				       '.'.$r->{'name'};
			}
		}

	# Validate TTL
	if ($in{'ttl_def'}) {
		delete($r->{'ttl'});
		}
	else {
		$in{'ttl'} =~ /^\d+$/ && $in{'ttl'} > 0 ||
			&error($text{'record_ettl'});
		$in{'ttl_units'} =~ /^[a-z]$/i ||
			&error($text{'record_ettlunits'});
		$r->{'ttl'} = $in{'ttl'}.$in{'ttl_units'};
		}

	if (&supports_dns_comments($d)) {
		# Save comment
		$r->{'comment'} = $in{'comment'};
		}

	# Validate values
	@vals = @{$t->{'values'}};
	$r->{'values'} = [ ];
	for(my $i=0; $i<@vals; $i++) {
		$v = $in{'value_'.$i};
		$v =~ s/\r//g;
		$v =~ s/\n/ /g;
		$re = $vals[$i]->{'regexp'};
		$fn = $vals[$i]->{'func'};
		!$re || $v =~ /$re/ ||
			&error(&text('record_evalue', $vals[$i]->{'desc'}));
		$err = $fn && &$fn($v);
		$err && &error($err);
		if ($vals[$i]->{'dot'} && $v =~ /\./ && $v !~ /\.$/) {
			# Append dot to value, in case user forgot it
			$v .= ".";
			}
		push(@{$r->{'values'}}, $v);
		}

	# Can be proxied
	$r->{'proxied'} = $in{'proxyit'}
		if ($r->{'type'} =~ /^(A|AAAA|CNAME)$/);

	# Check for CNAME collision
	if ($r->{'type'} eq 'CNAME') {
		$newrecs = [ @$recs ];
		push(@$newrecs, $r) if ($in{'type'});
		%clash = map { lc($_->{'name'}), $_ }
			     grep { $_ ne $r } @$newrecs;
		foreach $e (@$newrecs) {
			if ($e->{'type'} =~ /^(CNAME|A|AAAA|MX)$/ &&
			    $clash{lc($r->{'name'})}) {
				&error(&text('record_ecname', $r->{'name'}));
				}
			}
		}

	if ($in{'type'}) {
		# Create the record
		&create_dns_record($recs, $file, $r);
		}
	else {
		# Just update it
		&modify_dns_record($recs, $file, $r);
		}
	}
$err = &post_records_change($d, $recs, $file);
&release_lock_dns($d);
&reload_bind_records($d);
&run_post_actions_silently();
&webmin_log($in{'delete'} ? 'delete' : $in{'type'} ? 'create' : 'modify',
	    'record', $d->{'dom'}, $r);
&error(&text('record_epost', $err)) if ($err);
&redirect("list_records.cgi?dom=$in{'dom'}&show=$in{'show'}");

