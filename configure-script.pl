#!/usr/local/bin/perl
package virtual_server;

use File::Basename;

=head1 configure-script.pl

Configure web app script

This command can be used to modify web application settings, perform backups,
make clones and carry out other administrative tasks, if supported by the
application.

See the usage by calling the C<--help> flag with the script function for more
information on how to use this command, as it's specific to the web app
script type.

=cut

if (!$module_name) {
	$main::no_acl_check++;
	$ENV{'WEBMIN_CONFIG'} ||= "/etc/webmin";
	$ENV{'WEBMIN_VAR'} ||= "/var/webmin";
	if ($0 =~ /^(.*)\/[^\/]+$/) {
		chdir($pwd = $1);
		}
	else {
		chop($pwd = `pwd`);
		}
	$0 = "$pwd/configure-script.pl";
	require './virtual-server-lib.pl';
	}

# Load all modules that can configure web app scripts
my @mods = grep { $_->{'config_script'} } &get_all_module_infos();
foreach my $mod (@mods) {
	&foreign_require($mod->{'dir'});
	}

# Pre-process args to get web app name
our $web_app_name;
for (my $i=0; $i<@ARGV; $i++) {
	if ($ARGV[$i] eq '--script-type' && $i+1 < @ARGV) {
		$web_app_name = $ARGV[$i+1];
		last;
		}
	}

# Check for missing --name parameter
if (!$web_app_name) {
	&usage("Missing script type name");
	}

# Locate the usage and CLI handlers for this script type
my $script_usage_func = &script_find_kit_func(\@mods, $web_app_name, 'usage');
my $script_cli        = &script_find_kit_func(\@mods, $web_app_name, 'cli');

# Bail out if there’s no CLI handler
if (!$script_cli) {
	usage("Script '$web_app_name' does not support configure API");
	}

# Parse common command-line flags
&parse_common_cli_flags(\@ARGV);

# Call the script-specific CLI function
$script_cli->(\@ARGV);

# Expandable usage function
sub usage
{
print "$_[0]\n\n" if ($_[0]);
print "Configure web app script\n\n";
print "virtualmin configure-script --script-type name";
if (defined(&$script_usage_func)) {
	$script_usage_func->($web_app_name);
	}
else {
	print "\n";
	}
exit(1);
}
