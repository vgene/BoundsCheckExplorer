#include <stdio.h>
#include <stdlib.h>
#include <vector>
#include <fstream>
#include <iostream>
using namespace std;

extern "C" {
  void loop_exit(int numLoops);
  void loop_invocation(int numLoops);
  void outer_prof_init(int numLoops);

  void ProfFinish(void);

  static unsigned long rdtsc(void) {
    unsigned long high;
    unsigned long low;
    __asm__ volatile ("rdtsc" : "=a" (low), "=d" (high));
    return (high << 32) | low;
  }
}

vector<unsigned long> *invocations;
vector<unsigned long> *time_elapse;
vector<unsigned long> *begin_ts_v;
unsigned long begin_ts;
unsigned int totalNumLoops;

void loop_exit(int numLoops) {
  unsigned long end_ts = rdtsc();

#ifdef DEBUG  
  if (begin_ts == 0) {
    cerr << "No begin timestamp! Loop ID: " << numLoops  << endl;
  }
#endif

  (*time_elapse)[numLoops] += end_ts - (*begin_ts_v)[numLoops];
  begin_ts = 0;
}

void loop_invocation(int numLoops) {
  (*invocations)[numLoops]++;
#ifdef DEBUG  
  if (begin_ts!= 0) {
    cerr << "Nested Loop! Loop ID: " << numLoops << endl;
  }
#endif

  begin_ts= rdtsc();
  (*begin_ts_v)[numLoops] = begin_ts;
}

// careful! no global ctor yet, don't use cout
void outer_prof_init(int total) {
  totalNumLoops = total;

  invocations = new vector<unsigned long>(totalNumLoops, 0);
  time_elapse = new vector<unsigned long>(totalNumLoops, 0);
  begin_ts_v= new vector<unsigned long>(totalNumLoops, 0);
  begin_ts = 0;

  atexit(ProfFinish);
}

/* Finish up the profiler, print profile
 */
void ProfFinish() {
  ofstream file("outer_loop_prof.txt");

  file << "#LoopID #invocation #total_cycles" << endl;
  for (int i = 0; i < totalNumLoops; i++) {
    file << i << " " << (*invocations)[i] << " " << (*time_elapse)[i] << endl;
  }

  file.close();
}
