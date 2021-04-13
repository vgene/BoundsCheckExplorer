#! /usr/bin/perl -w
##--------------------------------------------------------------------##
##--- The cache simulation framework: instrumentation, recording   ---##
##--- and results printing.                                        ---##
##---                                           callgrind_annotate ---##
##--------------------------------------------------------------------##

#  This file is part of Callgrind, a cache-simulator and call graph
#  tracer built on Valgrind.
#
#  Copyright (C) 2003-2017 Josef Weidendorfer
#     Josef.Weidendorfer@gmx.de
#
#  This file is based heavily on cg_annotate, part of Valgrind.
#  Copyright (C) 2002-2017 Nicholas Nethercote
#     njn@valgrind.org
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#
#  The GNU General Public License is contained in the file COPYING.

#----------------------------------------------------------------------------
# Annotator for cachegrind/callgrind. 
#
# File format is described in /docs/techdocs.html.
#
# Performance improvements record, using cachegrind.out for cacheprof, doing no
# source annotation (irrelevant ones removed):
#                                                               user time
# 1. turned off warnings in add_hash_a_to_b()                   3.81 --> 3.48s
#    [now add_array_a_to_b()]
# 6. make line_to_CC() return a ref instead of a hash           3.01 --> 2.77s
#
#10. changed file format to avoid file/fn name repetition       2.40s
#    (not sure why higher;  maybe due to new '.' entries?)
#11. changed file format to drop unnecessary end-line "."s      2.36s
#    (shrunk file by about 37%)
#12. switched from hash CCs to array CCs                        1.61s
#13. only adding b[i] to a[i] if b[i] defined (was doing it if
#    either a[i] or b[i] was defined, but if b[i] was undefined
#    it just added 0)                                           1.48s
#14. Stopped converting "." entries to undef and then back      1.16s
#15. Using foreach $i (x..y) instead of for ($i = 0...) in
#    add_array_a_to_b()                                         1.11s
#
# Auto-annotating primes:
#16. Finding count lengths by int((length-1)/3), not by
#    commifying (halves the number of commify calls)            1.68s --> 1.47s

use strict;

#----------------------------------------------------------------------------
# Overview: the running example in the comments is for:
#   - events = A,B,C,D
#   - --show=C,A,D
#   - --sort=D,C
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
# Global variables, main data structures
#----------------------------------------------------------------------------
# CCs are arrays, the counts corresponding to @events, with 'undef'
# representing '.'.  This makes things fast (faster than using hashes for CCs)
# but we have to use @sort_order and @show_order below to handle the --sort and
# --show options, which is a bit tricky.
#----------------------------------------------------------------------------

# Total counts for summary (an array reference).
my $summary_CC;
my $totals_CC;
my $summary_calculated = 0;

# Totals for each function, for overall summary.
# hash(filename:fn_name => CC array)
my %fn_totals;

# Individual CCs, organised by filename and line_num for easy annotation.
# hash(filename => hash(line_num => CC array))
my %all_ind_CCs;

# Files chosen for annotation on the command line.  
# key = basename (trimmed of any directory), value = full filename
my %user_ann_files;

# Generic description string.
my $desc = "";

# Command line of profiled program.
my $cmd = "";

# Info on the profiled process.
my $creator = "";
my $pid = "";
my $part = "";
my $thread = "";

# Positions used for cost lines; default: line numbers
my $has_line = 1;
my $has_addr = 0;

# Events in input file, eg. (A,B,C,D)
my @events;
my $events;

# Events to show, from command line, eg. (C,A,D)
my @show_events;
                        #push(@uncheck_ln_list, line_num[0]);
                        #push(@uncheck_count_list, $src_file_CCs->{$.});
                        #push(@file_list, $full_file_name);
                        #push(@fn_list, $func_of_line{$src_file,$.};
my @uncheck_count_list;
my @uncheck_ln_list;
my @file_list;
my @fn_list;

# Map from @show_events indices to @events indices, eg. (2,0,3).  Gives the
# order in which we must traverse @events in order to show the @show_events, 
# eg. (@events[$show_order[1]], @events[$show_order[2]]...) = @show_events.
# (Might help to think of it like a hash (0 => 2, 1 => 0, 2 => 3).)
my @show_order;

# Print out the function totals sorted by these events, eg. (D,C).
my @sort_events;

# Map from @sort_events indices to @events indices, eg. (3,2).  Same idea as
# for @show_order.
my @sort_order;

# Thresholds, one for each sort event (or default to 1 if no sort events
# specified).  We print out functions and do auto-annotations until we've
# handled this proportion of all the events thresholded.
my @thresholds;

my $default_threshold = 99;

my $single_threshold  = $default_threshold;

# If on, show a percentage for each non-zero count.
my $show_percs = 1;

# If on, automatically annotates all files that are involved in getting over
# all the threshold counts.
my $auto_annotate = 1;

# Number of lines to show around each annotated line.
my $context = 8;

# Directories in which to look for annotation files.
my @include_dirs = ("");

# Verbose mode
my $verbose = "1";

# Inclusive statistics (with subroutine events)
my $inclusive = 0;

# Inclusive totals for each function, for overall summary.
# hash(filename:fn_name => CC array)
my %cfn_totals;

# hash( file:func => [ called file:func ])
my $called_funcs;

# hash( file:func => [ calling file:func ])
my $calling_funcs;

# hash( file:func,line => [called file:func ])
my $called_from_line;

# hash( file:func,line => file:func
my %func_of_line;

# hash (file:func => object name)
my %obj_name;

# Print out the callers of a function
my $tree_caller = 0;

# Print out the called functions
my $tree_calling = 0;

# hash( file:func,cfile:cfunc => call CC[])
my %call_CCs;

# hash( file:func,cfile:cfunc => call counter)
my %call_counter;

# hash(context, index) => realname for compressed traces
my %compressed;

# Input file name, will be set in process_cmd_line
my $input_file = "";

# Version number
my $version = "3.15";

# Usage message.
my $usage = <<END
usage: callgrind_annotate [options] [callgrind-out-file [source-files...]]

  options for the user, with defaults in [ ], are:
    -h --help             show this message
    --version             show version
    --show=A,B,C          only show figures for events A,B,C [all]
    --threshold=<0--100>  percentage of counts (of primary sort event) we
                          are interested in [$default_threshold%]
    --sort=A,B,C          sort columns by events A,B,C [event column order]
                          Each event can optionally be followed by a :
                          and a threshold percentage. If some event specific
                          threshold are given, --threshold value is ignored.
    --show-percs=yes|no   show a percentage for each non-zero count [yes]
    --auto=yes|no         annotate all source files containing functions
                          that helped reach the event count threshold [yes]
    --context=N           print N lines of context before and after
                          annotated lines [8]
    --inclusive=yes|no    add subroutine costs to functions calls [no]
    --tree=none|caller|   print for each function their callers,
           calling|both   the called functions or both [none]
    -I --include=<dir>    add <dir> to list of directories to search for 
                          source files

END
;

# Used in various places of output.
my $fancy = '-' x 80 . "\n";

sub safe_div($$)
{
    my ($x, $y) = @_;
    return ($y == 0 ? 0 : $x / $y);
}

#-----------------------------------------------------------------------------
# Argument and option handling
#-----------------------------------------------------------------------------
sub process_cmd_line() 
{
    for my $arg (@ARGV) { 

        # Option handling
        if ($arg =~ /^-/) {

            # --version
            if ($arg =~ /^--version$/) {
                die("callgrind_annotate-$version\n");

            # --show=A,B,C
            } elsif ($arg =~ /^--show=(.*)$/) {
                @show_events = split(/,/, $1);

            # --sort=A,B,C
            } elsif ($arg =~ /^--sort=(.*)$/) {
                @sort_events = split(/,/, $1);
                my $th_specified = 0;
                foreach my $i (0 .. scalar @sort_events - 1) {
                    if ($sort_events[$i] =~ /.*:([\d\.]+)%?$/) {
                        my $th = $1;
                        ($th >= 0 && $th <= 100) or die($usage);
                        $sort_events[$i] =~ s/:.*//;
                        $thresholds[$i] = $th;
                        $th_specified = 1;
                    } else {
                        $thresholds[$i] = 0;
                    }
                }
                if (not $th_specified) {
                    @thresholds = ();
                }

            # --threshold=X (tolerates a trailing '%')
            } elsif ($arg =~ /^--threshold=([\d\.]+)%?$/) {
                $single_threshold = $1;
                ($1 >= 0 && $1 <= 100) or die($usage);

            # --show-percs=yes|no
            } elsif ($arg =~ /^--show-percs=yes$/) {
                $show_percs = 1;
            } elsif ($arg =~ /^--show-percs=no$/) {
                $show_percs = 0;

            # --auto=yes|no
            } elsif ($arg =~ /^--auto=(yes|no)$/) {
                $auto_annotate = 1 if ($1 eq "yes");
                $auto_annotate = 0 if ($1 eq "no");

            # --context=N
            } elsif ($arg =~ /^--context=([\d\.]+)$/) {
                $context = $1;
                if ($context < 0) {
                    die($usage);
                }

            # --inclusive=yes|no
            } elsif ($arg =~ /^--inclusive=(yes|no)$/) {
                $inclusive = 1 if ($1 eq "yes");
                $inclusive = 0 if ($1 eq "no");

            # --tree=none|caller|calling|both
            } elsif ($arg =~ /^--tree=(none|caller|calling|both)$/) {
                $tree_caller  = 1 if ($1 eq "caller" || $1 eq "both");
                $tree_calling = 1 if ($1 eq "calling" || $1 eq "both");

            # --include=A,B,C
            } elsif ($arg =~ /^(-I|--include)=(.*)$/) {
                my $inc = $2;
                $inc =~ s|/$||;         # trim trailing '/'
                push(@include_dirs, "$inc/");

            } else {            # -h and --help fall under this case
                die($usage);
            }

        # Argument handling -- annotation file checking and selection.
        # Stick filenames into a hash for quick 'n easy lookup throughout
        } else {
	  if ($input_file eq "") {
	    $input_file = $arg;
	  }
	  else {
            my $readable = 0;
            foreach my $include_dir (@include_dirs) {
                if (-r $include_dir . $arg) {
                    $readable = 1;
                }
            }
            $readable or die("File $arg not found in any of: @include_dirs\n");
            $user_ann_files{$arg} = 1;
        } 
    }
    }

    if ($input_file eq "") {
      $input_file = (<callgrind.out*>)[0];
      if (!defined $input_file) {
	  $input_file = (<cachegrind.out*>)[0];
      }

      (defined $input_file) or die($usage);
      print "Reading data from '$input_file'...\n";
    }
}

#-----------------------------------------------------------------------------
# Reading of input file
#-----------------------------------------------------------------------------
sub max ($$) 
{
    my ($x, $y) = @_;
    return ($x > $y ? $x : $y);
}

# Add the two arrays;  any '.' entries are ignored.  Two tricky things:
# 1. If $a2->[$i] is undefined, it defaults to 0 which is what we want; we turn
#    off warnings to allow this.  This makes things about 10% faster than
#    checking for definedness ourselves.
# 2. We don't add an undefined count or a ".", even though it's value is 0,
#    because we don't want to make an $a2->[$i] that is undef become 0
#    unnecessarily.
sub add_array_a_to_b ($$) 
{
    my ($a1, $a2) = @_;

    my $n = max(scalar @$a1, scalar @$a2);
    $^W = 0;
    foreach my $i (0 .. $n-1) {
        $a2->[$i] += $a1->[$i] if (defined $a1->[$i] && "." ne $a1->[$i]);
    }
    $^W = 1;
}

# Is this a line with all events zero?
sub is_zero ($)
{
    my ($CC) = @_;
    my $isZero = 1;
    foreach my $i (0 .. (scalar @$CC)-1) {
	$isZero = 0 if ($CC->[$i] >0);
    }
    return $isZero;
}

# Add each event count to the CC array.  '.' counts become undef, as do
# missing entries (implicitly).
sub line_to_CC ($)
{
    my @CC = (split /\s+/, $_[0]);
    (@CC <= @events) or die("Line $.: too many event counts\n");
    return \@CC;
}

sub uncompressed_name($$)
{
   my ($context, $name) = @_;

   if ($name =~ /^\((\d+)\)\s*(.*)$/) {
     my $index = $1;
     my $realname = $2;

     if ($realname eq "") {
       $realname = $compressed{$context,$index};
     }
     else {
       $compressed{$context,$index} = $realname;
     }
     return $realname;
   }
   return $name;
}

sub read_input_file() 
{
    open(INPUTFILE, "< $input_file") || die "File $input_file not opened\n";

    my $line;

    # Read header
    while(<INPUTFILE>) {

      # Skip comments and empty lines.
      if (/^\s*$/ || /^\#/) { ; }

      elsif (/^version:\s*(\d+)/) {
	# Can't read format with major version > 1
	($1<2) or die("Can't read format with major version $1.\n");
      }

      elsif (/^pid:\s+(.*)$/) { $pid = $1;  }
      elsif (/^thread:\s+(.*)$/) { $thread = $1;  }
      elsif (/^part:\s+(.*)$/) { $part = $1;  }
      elsif (/^desc:\s+(.*)$/) {
	my $dline = $1;
	# suppress profile options in description output
	if ($dline =~ /^Option:/) {;}
	else { $desc .= "$dline\n"; }
      }
      elsif (/^cmd:\s+(.*)$/)  { $cmd = $1; }
      elsif (/^creator:\s+(.*)$/)  { $creator = $1; }
      elsif (/^positions:\s+(.*)$/) {
	my $positions = $1;
	$has_line = ($positions =~ /line/);
	$has_addr = ($positions =~ /(addr|instr)/);
      }
      elsif (/^event:\s+.*$/) { 
        # ignore lines giving a long name to an event
      }
      elsif (/^events:\s+(.*)$/) {
	$events = $1;
	
	# events line is last in header
	last;
      }
      else {
	warn("WARNING: header line $. malformed, ignoring\n");
	if ($verbose) { chomp; warn("    line: '$_'\n"); }
      }
    }

    # Read "events:" line.  We make a temporary hash in which the Nth event's
    # value is N, which is useful for handling --show/--sort options below.
    ($events ne "") or die("Line $.: missing events line\n");
    @events = split(/\s+/, $events);
    my %events;
    my $n = 0;
    foreach my $event (@events) {
        $events{$event} = $n;
        $n++
    }

    # If no --show arg give, default to showing all events in the file.
    # If --show option is used, check all specified events appeared in the
    # "events:" line.  Then initialise @show_order.
    if (@show_events) {
        foreach my $show_event (@show_events) {
            (defined $events{$show_event}) or 
                die("--show event `$show_event' did not appear in input\n");
        }
    } else {
        @show_events = @events;
    }
    foreach my $show_event (@show_events) {
        push(@show_order, $events{$show_event});
    }

    # Do as for --show, but if no --sort arg given, default to sorting by
    # column order (ie. first column event is primary sort key, 2nd column is
    # 2ndary key, etc).
    if (@sort_events) {
        foreach my $sort_event (@sort_events) {
            (defined $events{$sort_event}) or 
                die("--sort event `$sort_event' did not appear in input\n");
        }
    } else {
        @sort_events = @events;
    }
    foreach my $sort_event (@sort_events) {
        push(@sort_order, $events{$sort_event});
    }

    # If multiple threshold args weren't given via --sort, stick in the single
    # threshold (either from --threshold if used, or the default otherwise) for
    # the primary sort event, and 0% for the rest.
    if (not @thresholds) {
        foreach my $e (@sort_order) {
            push(@thresholds, 0);
        }
        $thresholds[0] = $single_threshold;
    } else {
        # setting $single_threshold to 0 to ensure the 'per event'
        # threshold logic is used.
        $single_threshold = 0;
    }

    # Current directory, used to strip from file names if absolute
    my $pwd = `pwd`;
    chomp $pwd;
    $pwd .= '/';

    my $curr_obj = "";
    my $curr_file;
    my $curr_fn;
    my $curr_name;
    my $curr_line_num = 0;
    my $prev_line_num = 0;

    my $curr_cobj = "";
    my $curr_cfile = "";
    my $curr_cfunc = "";
    my $curr_cname;
    my $curr_call_counter = 0;
    my $curr_cfn_CC = [];

    my $curr_fn_CC = [];
    my $curr_file_ind_CCs = {};     # hash(line_num => CC)

    # Read body of input file.
    while (<INPUTFILE>) {
        # Skip comments and empty lines.
        next if /^\s*$/ || /^\#/;

	$prev_line_num = $curr_line_num;

        s/^\+(\d+)/$prev_line_num+$1/e;
        s/^\-(\d+)/$prev_line_num-$1/e;
        s/^\*/$prev_line_num/e;
        if (s/^(-?\d+|0x\w+)\s+//) {
            $curr_line_num = $1;
	    if ($has_addr) {
	      if ($has_line) {
                s/^\+(\d+)/$prev_line_num+$1/e;
	        s/^\-(\d+)/$prev_line_num-$1/e;
                s/^\*/$prev_line_num/e;

	        if (s/^(\d+)\s+//) { $curr_line_num = $1; }
	      }
	      else { $curr_line_num = 0; }
	    }
            my $CC = line_to_CC($_);

	    if ($curr_call_counter>0) {
#	      print "Read ($curr_name => $curr_cname) $curr_call_counter\n";

	      if (!defined $call_CCs{$curr_name,$curr_cname}) {
		$call_CCs{$curr_name,$curr_cname} = [];
		$call_counter{$curr_name,$curr_cname} = 0;
	      }
	      add_array_a_to_b($CC, $call_CCs{$curr_name,$curr_cname});
	      $call_counter{$curr_name,$curr_cname} += $curr_call_counter;

	      my $tmp = $called_from_line->{$curr_file,$curr_line_num};
	      if (!defined $tmp) {
		$func_of_line{$curr_file,$curr_line_num} = $curr_name;
	      }
	      $tmp = {} unless defined $tmp;
	      $$tmp{$curr_cname} = 1;
	      $called_from_line->{$curr_file,$curr_line_num} = $tmp;
	      if (!defined $call_CCs{$curr_name,$curr_cname,$curr_line_num}) {
		$call_CCs{$curr_name,$curr_cname,$curr_line_num} = [];
		$call_counter{$curr_name,$curr_cname,$curr_line_num} = 0;
	      }
	      add_array_a_to_b($CC, $call_CCs{$curr_name,$curr_cname,$curr_line_num});
	      $call_counter{$curr_name,$curr_cname,$curr_line_num} += $curr_call_counter;

	      $curr_call_counter = 0;

	      # inclusive costs
	      $curr_cfn_CC = $cfn_totals{$curr_cname};
	      $curr_cfn_CC = [] unless (defined $curr_cfn_CC);
	      add_array_a_to_b($CC, $curr_cfn_CC);
	      $cfn_totals{$curr_cname} = $curr_cfn_CC;

	      if ($inclusive) {
		add_array_a_to_b($CC, $curr_fn_CC);
	      }
	      next;
	    }

            add_array_a_to_b($CC, $curr_fn_CC);

            # If curr_file is selected, add CC to curr_file list.  We look for
            # full filename matches;  or, if auto-annotating, we have to
            # remember everything -- we won't know until the end what's needed.
            if ($auto_annotate || defined $user_ann_files{$curr_file}) {
                my $tmp = $curr_file_ind_CCs->{$curr_line_num};
                $tmp = [] unless defined $tmp;
                add_array_a_to_b($CC, $tmp);
                $curr_file_ind_CCs->{$curr_line_num} = $tmp;
            }

        } elsif (s/^fn=(.*)$//) {
            # Commit result from previous function
            $fn_totals{$curr_name} = $curr_fn_CC if (defined $curr_name);

            # Setup new one
            $curr_fn = uncompressed_name("fn",$1);
            $curr_name = "$curr_file:$curr_fn";
	    $obj_name{$curr_name} = $curr_obj;
            $curr_fn_CC = $fn_totals{$curr_name};
            $curr_fn_CC = [] unless (defined $curr_fn_CC);

        } elsif (s/^ob=(.*)$//) {
            $curr_obj = uncompressed_name("ob",$1);

        } elsif (s/^fl=(.*)$//) {
            $all_ind_CCs{$curr_file} = $curr_file_ind_CCs 
                if (defined $curr_file);

            $curr_file = uncompressed_name("fl",$1);
            $curr_file =~ s/^\Q$pwd\E//;
            $curr_file_ind_CCs = $all_ind_CCs{$curr_file};
            $curr_file_ind_CCs = {} unless (defined $curr_file_ind_CCs);

        } elsif (s/^(fi|fe)=(.*)$//) {
            (defined $curr_name) or die("Line $.: Unexpected fi/fe line\n");
            $fn_totals{$curr_name} = $curr_fn_CC;
            $all_ind_CCs{$curr_file} = $curr_file_ind_CCs;

            $curr_file = uncompressed_name("fl",$2);
            $curr_file =~ s/^\Q$pwd\E//;
            $curr_name = "$curr_file:$curr_fn";
            $curr_file_ind_CCs = $all_ind_CCs{$curr_file};
            $curr_file_ind_CCs = {} unless (defined $curr_file_ind_CCs);
            $curr_fn_CC = $fn_totals{$curr_name};
            $curr_fn_CC = [] unless (defined $curr_fn_CC);

        } elsif (s/^cob=(.*)$//) {
	  $curr_cobj = uncompressed_name("ob",$1);

	} elsif (s/^cf[il]=(.*)$//) {
	  $curr_cfile = uncompressed_name("fl",$1);

	} elsif (s/^cfn=(.*)$//) {
	  $curr_cfunc = uncompressed_name("fn",$1);
	  if ($curr_cfile eq "") {
	    $curr_cname = "$curr_file:$curr_cfunc";
	  }
	  else {
	    $curr_cname = "$curr_cfile:$curr_cfunc";
	    $curr_cfile = "";
	  }

	  my $tmp = $calling_funcs->{$curr_cname};
	  $tmp = {} unless defined $tmp;
	  $$tmp{$curr_name} = 1;
	  $calling_funcs->{$curr_cname} = $tmp;
		
	  my $tmp2 = $called_funcs->{$curr_name};
	  $tmp2 = {} unless defined $tmp2;
	  $$tmp2{$curr_cname} = 1;
	  $called_funcs->{$curr_name} = $tmp2;

	} elsif (s/^calls=(\d+)//) {
	  $curr_call_counter = $1;

        } elsif (s/^(jump|jcnd)=//) {
	  #ignore jump information

        } elsif (s/^jfi=(.*)$//) {
          # side effect needed: possibly add compression mapping 
          uncompressed_name("fl",$1);
          # ignore jump information	

        } elsif (s/^jfn=(.*)$//) {
          # side effect needed: possibly add compression mapping
          uncompressed_name("fn",$1);
          # ignore jump information

        } elsif (s/^totals:\s+//) {
	    $totals_CC = line_to_CC($_);

        } elsif (s/^summary:\s+//) {
            $summary_CC = line_to_CC($_);

        } else {
            warn("WARNING: line $. malformed, ignoring\n");
	    if ($verbose) { chomp; warn("    line: '$_'\n"); }
        }
    }

    # Finish up handling final filename/fn_name counts
    $fn_totals{"$curr_file:$curr_fn"} = $curr_fn_CC
	if (defined $curr_file && defined $curr_fn);
    $all_ind_CCs{$curr_file} =
	$curr_file_ind_CCs if (defined $curr_file);

    # Correct inclusive totals
    if ($inclusive) {
      foreach my $name (keys %cfn_totals) {
	$fn_totals{$name} = $cfn_totals{$name};
      }
    }

    close(INPUTFILE);

    if ((not defined $summary_CC) || is_zero($summary_CC)) {
	$summary_CC = $totals_CC;

	# if neither 'summary:' nor 'totals:' line is given,
	# calculate summary from fn_totals hash
	if ((not defined $summary_CC) || is_zero($summary_CC)) {
	    $summary_calculated = 1;
	    $summary_CC = [];
	    foreach my $name (keys %fn_totals) {
		add_array_a_to_b($fn_totals{$name}, $summary_CC);
	    }
	}
    }
}

#-----------------------------------------------------------------------------
# Print options used
#-----------------------------------------------------------------------------
sub print_options ()
{
    print($fancy);
    print "Profile data file '$input_file'";
    if ($creator ne "") { print " (creator: $creator)"; }
    print "\n";

    print($fancy);
    print($desc);
    my $target = $cmd;
    if ($target eq "") { $target = "(unknown)"; }
    if ($pid ne "") {
      $target .= " (PID $pid";
      if ($part ne "") { $target .= ", part $part"; }
      if ($thread ne "") { $target .= ", thread $thread"; }
      $target .= ")";
    }
    print("Profiled target:  $target\n");
    print("Events recorded:  @events\n");
    print("Events shown:     @show_events\n");
    print("Event sort order: @sort_events\n");
    print("Thresholds:       @thresholds\n");

    my @include_dirs2 = @include_dirs;  # copy @include_dirs
    shift(@include_dirs2);       # remove "" entry, which is always the first
    unshift(@include_dirs2, "") if (0 == @include_dirs2); 
    my $include_dir = shift(@include_dirs2);
    print("Include dirs:     $include_dir\n");
    foreach my $include_dir (@include_dirs2) {
        print("                  $include_dir\n");
    }

    my @user_ann_files = keys %user_ann_files;
    unshift(@user_ann_files, "") if (0 == @user_ann_files); 
    my $user_ann_file = shift(@user_ann_files);
    print("User annotated:   $user_ann_file\n");
    foreach $user_ann_file (@user_ann_files) {
        print("                  $user_ann_file\n");
    }

    my $is_on = ($auto_annotate ? "on" : "off");
    print("Auto-annotation:  $is_on\n");
    print("\n");
}

#-----------------------------------------------------------------------------
# Print summary and sorted function totals
#-----------------------------------------------------------------------------
sub mycmp ($$) 
{
    my ($c, $d) = @_;

    # Iterate through sort events (eg. 3,2); return result if two are different
    foreach my $i (@sort_order) {
        my ($x, $y);
        $x = $c->[$i];
        $y = $d->[$i];
        $x = -1 unless defined $x;
        $y = -1 unless defined $y;

        my $cmp = $y <=> $x;        # reverse sort
        if (0 != $cmp) {
            return $cmp;
        }
    }
    # Exhausted events, equal
    return 0;
}

sub commify ($) {
    my ($val) = @_;
    1 while ($val =~ s/^(\d+)(\d{3})/$1,$2/);
    return $val;
}

# Because the counts can get very big, and we don't want to waste screen space
# and make lines too long, we compute exactly how wide each column needs to be
# by finding the widest entry for each one.
sub compute_CC_col_widths (@) 
{
    my @CCs = @_;
    my $CC_col_widths = [];

    # Initialise with minimum widths (from event names)
    foreach my $event (@events) {
        push(@$CC_col_widths, length($event));
    }
    
    # Find maximum width count for each column.  @CC_col_width positions
    # correspond to @CC positions.
    foreach my $CC (@CCs) {
        foreach my $i (0 .. scalar(@$CC)-1) {
            if (defined $CC->[$i]) {
                # Find length, accounting for commas that will be added, and
                # possibly a percentage.
                my $length = length $CC->[$i];
                my $width = $length + int(($length - 1) / 3);
                if ($show_percs) {
                    $width += 9;    # e.g. " (12.34%)" is 9 chars
                }
                $CC_col_widths->[$i] = max($CC_col_widths->[$i], $width); 
            }
        }
    }
    return $CC_col_widths;
}

# Print the CC with each column's size dictated by $CC_col_widths.
sub print_CC ($$) 
{
    my ($CC, $CC_col_widths) = @_;

    foreach my $i (@show_order) {
        my $count = (defined $CC->[$i] ? commify($CC->[$i]) : ".");

        my $perc = "";
        if ($show_percs) {
            if (defined $CC->[$i] && $CC->[$i] != 0) {
                # Try our best to keep the number fitting into 5 chars. This
                # requires dropping a digit after the decimal place if it's
                # sufficiently negative (e.g. "-10.0") or positive (e.g.
                # "100.0"). Thanks to diffs it's possible to have even more
                # extreme values, like "-100.0" or "1000.0"; those rare case
                # will end up with slightly wrong indenting, oh well.
                $perc = safe_div($CC->[$i] * 100, $summary_CC->[$i]);
                $perc = (-9.995 < $perc && $perc < 99.995)
                      ? sprintf(" (%5.2f%%)", $perc)
                      : sprintf(" (%5.1f%%)", $perc);
            } else {
                # Don't show percentages for "." and "0" entries.
                $perc = "         ";
            }
        }

        # $reps will be negative for the extreme values mentioned above. The
        # use of max() avoids a possible warning about a negative repeat count.
        my $text = $count . $perc;
        my $len = length($text);
        my $reps = $CC_col_widths->[$i] - length($text);
        my $space = ' ' x max($reps, 0);
        print("$space$text ");
    }
}

sub print_events ($)
{
    my ($CC_col_widths) = @_;

    foreach my $i (@show_order) { 
        my $event       = $events[$i];
        my $event_width = length($event);
        my $col_width   = $CC_col_widths->[$i];
        my $space       = ' ' x ($col_width - $event_width);
        print("$event$space ");
    }
}

# Prints summary and function totals (with separate column widths, so that
# function names aren't pushed over unnecessarily by huge summary figures).
# Also returns a hash containing all the files that are involved in getting the
# events count above the thresholds (ie. all the interesting ones).
sub print_summary_and_fn_totals ()
{
    my @fn_fullnames = keys   %fn_totals;

    # Work out the size of each column for printing (summary and functions
    # separately).
    my $summary_CC_col_widths = compute_CC_col_widths($summary_CC);
    my      $fn_CC_col_widths = compute_CC_col_widths(values %fn_totals);

    # Header and counts for summary
    print($fancy);
    print_events($summary_CC_col_widths);
    print("\n");
    print($fancy);
    print_CC($summary_CC, $summary_CC_col_widths);
    print(" PROGRAM TOTALS");
    if ($summary_calculated) {
	print(" (calculated)");
    }
    print("\n\n");

    # Header for functions
    print($fancy);
    print_events($fn_CC_col_widths);
    print(" file:function\n");
    print($fancy);

    # Sort function names into order dictated by --sort option.
    @fn_fullnames = sort {
        mycmp($fn_totals{$a}, $fn_totals{$b}) || $a cmp $b
    } @fn_fullnames;


    # Assertion
    (scalar @sort_order == scalar @thresholds) or 
        die("sort_order length != thresholds length:\n",
            "  @sort_order\n  @thresholds\n");

    my $threshold_files       = {};
    # @curr_totals has the same shape as @sort_order and @thresholds
    my @curr_totals = ();
    foreach my $e (@thresholds) {
        push(@curr_totals, 0);
    }

    # Print functions, stopping when the threshold has been reached.
    foreach my $fn_name (@fn_fullnames) {
        # if $single_threshold is 100 the user want to see everything,
        # so do not enter the filtering logic, as truncation can cause
        # some functions to not be shown.
        if ($single_threshold < 100) {
            # Stop when we've reached all the thresholds
            my $reached_all_thresholds = 1;
            foreach my $i (0 .. scalar @thresholds - 1) {
                my $prop = $curr_totals[$i] * 100;
                if (defined $summary_CC->[$sort_order[$i]] &&
                    $summary_CC->[$sort_order[$i]] >0) {
                    $prop = $prop / $summary_CC->[$sort_order[$i]];
                }
                $reached_all_thresholds &&= ($prop >= $thresholds[$i]);
            }
            last if $reached_all_thresholds;
        }

	if ($tree_caller || $tree_calling) { print "\n"; }

	if ($tree_caller && ($fn_name ne "???:???")) {
	  # Print function callers
	  my $tmp1 = $calling_funcs->{$fn_name};
	  if (defined $tmp1) {
	    # Sort calling functions into order dictated by --sort option.
	    my @callings = sort {
	      mycmp($call_CCs{$a,$fn_name}, $call_CCs{$b,$fn_name})
	    } keys %$tmp1;
	    foreach my $calling (@callings) {
	      if (defined $call_counter{$calling,$fn_name}) {
		print_CC($call_CCs{$calling,$fn_name}, $fn_CC_col_widths);
		print" < $calling (";
		print commify($call_counter{$calling,$fn_name}) . "x)";
		if (defined $obj_name{$calling}) {
		  print " [$obj_name{$calling}]";
		}
		print "\n";
	      }
	    }
	  }
	}

        # Print function results
        my $fn_CC = $fn_totals{$fn_name};
        print_CC($fn_CC, $fn_CC_col_widths);
	if ($tree_caller || $tree_calling) { print " * "; }
        print(" $fn_name");
	if ((defined $obj_name{$fn_name}) &&
	    ($obj_name{$fn_name} ne "")) {
	  print " [$obj_name{$fn_name}]";
	}
	print "\n";

	if ($tree_calling && ($fn_name ne "???:???")) {
	  # Print called functions
	  my $tmp2 = $called_funcs->{$fn_name};
	  if (defined $tmp2) {
	    # Sort called functions into order dictated by --sort option.
	    my @calleds = sort {
	      mycmp($call_CCs{$fn_name,$a}, $call_CCs{$fn_name,$b})
	    } keys %$tmp2;
	    foreach my $called (@calleds) {
	      if (defined $call_counter{$fn_name,$called}) {
		print_CC($call_CCs{$fn_name,$called}, $fn_CC_col_widths);
		print" >   $called (";
		print commify($call_counter{$fn_name,$called}) . "x)";
		if (defined $obj_name{$called}) {
		  print " [$obj_name{$called}]";
		}
		print "\n";
	      }
	    }
	  }
	}

        # Update the threshold counts
        my $filename = $fn_name;
        $filename =~ s/:.+$//;    # remove function name
        $threshold_files->{$filename} = 1;
        foreach my $i (0 .. scalar @sort_order - 1) {
	  if ($inclusive) {
	    $curr_totals[$i] = $summary_CC->[$sort_order[$i]] -
                               $fn_CC->[$sort_order[$i]]
	      if (defined $fn_CC->[$sort_order[$i]]);
	  } else {
            $curr_totals[$i] += $fn_CC->[$sort_order[$i]] 
                if (defined $fn_CC->[$sort_order[$i]]);
        }
    }
    }
    print("\n");

    return $threshold_files;
}

#-----------------------------------------------------------------------------
# Annotate selected files
#-----------------------------------------------------------------------------

# Issue a warning that the source file is more recent than the input file. 
sub warning_on_src_more_recent_than_inputfile ($)
{
    my $src_file = $_[0];

    my $warning = <<END
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@ WARNING @@ WARNING @@ WARNING @@ WARNING @@ WARNING @@ WARNING @@ WARNING @@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ Source file '$src_file' is more recent than input file '$input_file'.
@ Annotations may not be correct.
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

END
;
    print($warning);
}

# If there is information about lines not in the file, issue a warning
# explaining possible causes.
sub warning_on_nonexistent_lines ($$$)
{
    my ($src_more_recent_than_inputfile, $src_file, $excess_line_nums) = @_;
    my $cause_and_solution;

    if ($src_more_recent_than_inputfile) {
        $cause_and_solution = <<END
@@ cause:    '$src_file' has changed since information was gathered.
@@           If so, a warning will have already been issued about this.
@@ solution: Recompile program and rerun under "valgrind --cachesim=yes" to 
@@           gather new information.
END
    # We suppress warnings about .h files
    } elsif ($src_file =~ /\.h$/) {
        $cause_and_solution = <<END
@@ cause:    bug in the Valgrind's debug info reader that screws up with .h
@@           files sometimes
@@ solution: none, sorry
END
    } else {
        $cause_and_solution = <<END
@@ cause:    not sure, sorry
END
    }

    my $warning = <<END
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@ WARNING @@ WARNING @@ WARNING @@ WARNING @@ WARNING @@ WARNING @@ WARNING @@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@
@@ Information recorded about lines past the end of '$src_file'.
@@
@@ Probable cause and solution:
$cause_and_solution@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
END
;
    print($warning);
}

sub annotate_ann_files($)
{
    my ($threshold_files) = @_; 

    my %all_ann_files;
    my @unfound_auto_annotate_files;
    my $printed_totals_CC = [];

    # If auto-annotating, add interesting files (but not "???")
    if ($auto_annotate) {
        delete $threshold_files->{"???"};
        %all_ann_files = (%user_ann_files, %$threshold_files) 
    } else {
        %all_ann_files = %user_ann_files;
    }

    # Track if we did any annotations.
    my $did_annotations = 0;

    LOOP:
    foreach my $src_file (keys %all_ann_files) {

        my $opened_file = "";
        my $full_file_name = "";
        foreach my $include_dir (@include_dirs) {
            my $try_name = $include_dir . $src_file;
            if (open(INPUTFILE, "< $try_name")) {
                $opened_file    = $try_name;
                $full_file_name = ($include_dir eq "" 
                                  ? $src_file 
                                  : "$include_dir + $src_file"); 
                last;
            }
        }
        
        if (not $opened_file) {
            # Failed to open the file.  If chosen on the command line, die.
            # If arose from auto-annotation, print a little message.
            if (defined $user_ann_files{$src_file}) {
                die("File $src_file not opened in any of: @include_dirs\n");

            } else {
                push(@unfound_auto_annotate_files, $src_file);
            }

        } else {
            # File header (distinguish between user- and auto-selected files).
            print("$fancy");
            my $ann_type = 
                (defined $user_ann_files{$src_file} ? "User" : "Auto");
            print("-- $ann_type-annotated source: $full_file_name\n");
            print("$fancy");

            # Get file's CCs
            my $src_file_CCs = $all_ind_CCs{$src_file};
            if (!defined $src_file_CCs) {
                print("  No information has been collected for $src_file\n\n");
                next LOOP;
            }
        
            $did_annotations = 1;
            
            # Numeric, not lexicographic sort!
            my @line_nums = sort {$a <=> $b} keys %$src_file_CCs;  

            # If $src_file more recent than cachegrind.out, issue warning
            my $src_more_recent_than_inputfile = 0;
            if ((stat $opened_file)[9] > (stat $input_file)[9]) {
                $src_more_recent_than_inputfile = 1;
                warning_on_src_more_recent_than_inputfile($src_file);
            }

            # Work out the size of each column for printing
            my $CC_col_widths = compute_CC_col_widths(values %$src_file_CCs);

            # Events header
            print_events($CC_col_widths);
            print("\n\n");

            # Shift out 0 if it's in the line numbers (from unknown entries,
            # likely due to bugs in Valgrind's stabs debug info reader)
            shift(@line_nums) if (0 == $line_nums[0]);

            # Finds interesting line ranges -- all lines with a CC, and all
            # lines within $context lines of a line with a CC.
            my $n = @line_nums;
            my @pairs;
            for (my $i = 0; $i < $n; $i++) {
                push(@pairs, $line_nums[$i] - $context);   # lower marker
                while ($i < $n-1 && 
                       $line_nums[$i] + 2*$context >= $line_nums[$i+1]) {
                    $i++;
                }
                push(@pairs, $line_nums[$i] + $context);   # upper marker
            }

            # Annotate chosen lines, tracking total counts of lines printed
            $pairs[0] = 1 if ($pairs[0] < 1);
            while (@pairs) {
                my $low  = shift @pairs;
                my $high = shift @pairs;
                while ($. < $low-1) {
                    my $tmp = <INPUTFILE>;
                    last unless (defined $tmp);     # hack to detect EOF
                }
                my $src_line;
                # Print line number, unless start of file
                print("-- line $low " . '-' x 40 . "\n") if ($low != 1);
                while (($. < $high) && ($src_line = <INPUTFILE>)) {
                    if (index("$src_line", "\.get_unchecked") != -1) {
                        push(@uncheck_ln_list, $.);
                        push(@uncheck_count_list, $src_file_CCs->{$.});
                        push(@file_list, $full_file_name);

                        my $tmp  = $called_from_line->{$src_file,$.};
                        if (defined $tmp) {
                            push(@fn_list, $func_of_line{$src_file,$.});
                        }
                        else {
                            push(@fn_list, "");
                        }
                    }

                    if (defined $line_nums[0] && $. == $line_nums[0]) {
                        print_CC($src_file_CCs->{$.}, $CC_col_widths);
                        add_array_a_to_b($src_file_CCs->{$.}, 
                            $printed_totals_CC);
                        shift(@line_nums);

                    } else {
                        print_CC([], $CC_col_widths);
                    }

                    print(" $src_line");


                    my $tmp  = $called_from_line->{$src_file,$.};
                    my $func = $func_of_line{$src_file,$.};
                    if (defined $tmp) {
                        # Sort called functions into order dictated by --sort option.
                        my @calleds = sort {
                            mycmp($call_CCs{$func,$a}, $call_CCs{$func,$b})
                        } keys %$tmp;
                        foreach my $called (@calleds) {
                            if (defined $call_CCs{$func,$called,$.}) {
                                print_CC($call_CCs{$func,$called,$.}, $CC_col_widths);
                                print " => $called (";
                                print commify($call_counter{$func,$called,$.}) . "x)\n";
                            }
                        }
                    }
                }
                # Print line number, unless EOF
                if ($src_line) {
                    print("-- line $high " . '-' x 40 . "\n");
                } else {
                    last;
                }
            }

            # If there was info on lines past the end of the file...
            if (@line_nums) {
                foreach my $line_num (@line_nums) {
                    print_CC($src_file_CCs->{$line_num}, $CC_col_widths);
                    print(" <bogus line $line_num>\n");
                }
                print("\n");
                warning_on_nonexistent_lines($src_more_recent_than_inputfile,
                                             $src_file, \@line_nums);
            }
            print("\n");

            # Print summary of counts attributed to file but not to any
            # particular line (due to incomplete debug info).
            if ($src_file_CCs->{0}) {
                print_CC($src_file_CCs->{0}, $CC_col_widths);
                print(" <counts for unidentified lines in $src_file>\n\n");
            }
            
            close(INPUTFILE);
        }
    }

    # Print list of unfound auto-annotate selected files.
    if (@unfound_auto_annotate_files) {
        print("$fancy");
        print("The following files chosen for auto-annotation could not be found:\n");
        print($fancy);
        foreach my $f (sort @unfound_auto_annotate_files) {
            print("  $f\n");
        }
        print("\n");
    }

    # If we did any annotating, show how many events were covered by annotated
    # lines above.
    if ($did_annotations) {
        foreach (my $i = 0; $i < @$summary_CC; $i++) {
            # Some files (in particular the files produced by --xtree-memory)
            # have non additive self costs, so have a special case for these
            # to print all functions and also to avoid a division by 0.
            if ($summary_CC->[$i] == 0
                || $printed_totals_CC->[$i] > $summary_CC->[$i]) {
                # Set the summary_CC value equal to the printed_totals_CC value
                # so that the percentage printed by the print_CC call below is
                # 100%. This is ok because the summary_CC value is not used
                # again afterward.
                $summary_CC->[$i] = $printed_totals_CC->[$i];
            }
        }
        my $CC_col_widths = compute_CC_col_widths($printed_totals_CC);
        print($fancy);
        print_events($CC_col_widths);
        print("\n");
        print($fancy);
        print_CC($printed_totals_CC, $CC_col_widths);
        print(" events annotated\n\n");
    }
}

sub print_CC_one($) 
{
    my ($CC) = @_;

    foreach my $i (@show_order) {
        my $count = (defined $CC->[$i] ? $CC->[$i]: "");

        my $perc = "";
        if ($show_percs) {
            if (defined $CC->[$i] && $CC->[$i] != 0) {
                # Try our best to keep the number fitting into 5 chars. This
                # requires dropping a digit after the decimal place if it's
                # sufficiently negative (e.g. "-10.0") or positive (e.g.
                # "100.0"). Thanks to diffs it's possible to have even more
                # extreme values, like "-100.0" or "1000.0"; those rare case
                # will end up with slightly wrong indenting, oh well.
                $perc = safe_div($CC->[$i] * 100, $summary_CC->[$i]);
                $perc = (-9.995 < $perc && $perc < 99.995)
                      ? sprintf("%5.2f%%", $perc)
                      : sprintf("%5.1f%%", $perc);
            } else {
                # Don't show percentages for "." and "0" entries.
                $perc = "";
            }
        }

        # $reps will be negative for the extreme values mentioned above. The
        # use of max() avoids a possible warning about a negative repeat count.
        $perc=~ s/^\s+//;
        my $text = $count.",".$perc;
        print("$text");
    }
}

sub print_all_uncheck() {
    print("Start of get_unchecked stats\n");
    while (@uncheck_count_list) {
        print_CC_one(pop @uncheck_count_list);
        print(",");
        print(pop @uncheck_ln_list);
        print(",");
        print(pop @file_list);
        print(",");
        print(pop @fn_list);
        print("\n");
    }
}

#----------------------------------------------------------------------------
# "main()"
#----------------------------------------------------------------------------
process_cmd_line();
read_input_file();
print_options();
my $threshold_files = print_summary_and_fn_totals();
annotate_ann_files($threshold_files);

print_all_uncheck();

##--------------------------------------------------------------------##
##--- end                                           vg_annotate.in ---##
##--------------------------------------------------------------------##


