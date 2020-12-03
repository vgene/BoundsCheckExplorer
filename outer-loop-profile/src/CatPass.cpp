#include "llvm/ADT/SmallVector.h"
#include "llvm/Analysis/BasicAliasAnalysis.h"
#include "llvm/Analysis/LoopPass.h"
#include "llvm/Analysis/Passes.h"

#include "llvm/IR/CFG.h"
#include "llvm/IR/CallSite.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/PassManager.h"

#include "llvm/Pass.h"
#include "llvm/PassSupport.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"

#include <iostream>
#include <set>
#include <vector>
#include <map>

using namespace llvm;

namespace {

  struct OuterLoopProfInstr: public ModulePass{
    static char ID; 
    
    static StringRef getFunctionName(CallBase *call) {
        Function *fun = call->getCalledFunction();
        if (fun) // thanks @Anton Korobeynikov
            return fun->getName(); // inherited from llvm::Value
        else
            return StringRef("");
    }

    OuterLoopProfInstr() : ModulePass(ID) {}

    void visitAndRemoveFnRec(Function* f, std::set<Function*> &visited_fns, std::set<Function*> &keep_fns) {
      // visited
      if (visited_fns.find(f) != visited_fns.end())
        return;

      // mark visited
      visited_fns.insert(f);
      errs() << "examing " << f->getName() << '\n';

      // remove this from keep functions
      keep_fns.erase(f);

      for (BasicBlock &BB: *f){
        for (Instruction &I: BB) {
          if (CallBase* cs = dyn_cast<CallBase>(&I)) { 
            Function *f = cs->getCalledFunction();
            if (f) {
              if (f->isDeclaration()) continue;
              visitAndRemoveFnRec(f, visited_fns, keep_fns);
            }
          }
        }
      }
    }

    void instrumentProf(Loop *Lp, unsigned int id, Module* M){
      BasicBlock *preHeader;
      BasicBlock *header;

      header = Lp->getHeader();
      preHeader = Lp->getLoopPreheader();

      SmallVector<BasicBlock*, 16> exitBlocks;

      Lp->getExitBlocks(exitBlocks);

      // insert invocation function at end of preheader (called once prior to loop)
      const char* InvocName = "loop_invocation";
      FunctionCallee wrapper =  M->getOrInsertFunction(InvocName,
          Type::getVoidTy(M->getContext()), Type::getInt32Ty(M->getContext()));

      Constant *InvocFn = cast<Constant>(wrapper.getCallee());
      //sot
      //Type::getVoidTy(M->getContext()), Type::getInt32Ty(M->getContext()), (Type *)0);
      std::vector<Value*> Args(1);
      Args[0] = ConstantInt::get(Type::getInt32Ty(M->getContext()), id);

      assert(preHeader && "Null preHeader -- Did you run loopsimplify?");

      if (!preHeader->empty()) {
        CallInst::Create(InvocFn, Args, "", (preHeader->getTerminator()));
      }
      else {
        CallInst::Create(InvocFn, Args, "", (preHeader));
      }

      // insert loop end at beginning of exit blocks
      const char* LoopEndName = "loop_exit";
      FunctionCallee wrapper_end = M->getOrInsertFunction(LoopEndName,
          Type::getVoidTy(M->getContext()), Type::getInt32Ty(M->getContext()));

      Constant *LoopEndFn= cast<Constant>(wrapper_end.getCallee());
      //sot
      //Type::getVoidTy(M->getContext()), Type::getInt32Ty(M->getContext()), (Type *)0);

      std::set <BasicBlock*> BBSet;
      BBSet.clear();
      for(unsigned int i = 0; i != exitBlocks.size(); i++){
        // this ordering places iteration end before loop exit
        // make sure not inserting the same exit block more than once for a loop -PC 2/5/2009
        if (BBSet.find(exitBlocks[i])!=BBSet.end())
          continue;
        BBSet.insert(exitBlocks[i]);
        BasicBlock::iterator ii = exitBlocks[i]->getFirstInsertionPt();
        exitBlocks[i]->begin();
        //while (isa<PHINode>(ii)) { ii++; }
        //while (isaLAMP(ii)) { ii++; }

        //CallInst::Create(IterEndFn, "", ii);  // iter end placed before exit call

        CallInst::Create(LoopEndFn, Args, "", &*ii);
        //CallInst::Create(LoopEndFn, "", ii);  // loop exiting
      }
    }

    // 1. Need to run loopssa pass before
    // 2. Iterate all loops, check the depth, if is outermost loop, put in a list
    // 3. Go through all loops, find all functions called, remove them from the keep_fns set
    bool runOnModule(Module& M){

      std::map<Function*, std::vector<BasicBlock*>> map_fn_loops;

      for (auto IF = M.begin(), E = M.end(); IF != E; ++IF) {
        Function &F = *IF;
        if (F.isDeclaration()) continue;
        if (F.size() == 0) continue;  // not sure if this is necessary

        // get all outermost loops
        LoopInfo &LI = getAnalysis<LoopInfoWrapperPass>(F).getLoopInfo();
        for (auto i = LI.begin(); i != LI.end(); i++) {
          Loop *l = *i;
          if (l->getLoopDepth() == 1) {// outermost loop depth == 1
            auto header = l->getHeader();
            map_fn_loops[&F].push_back(header);
          }
        }
      }

      int total_loops = 0;
      std::set<Function*> visited_fns;
      std::set<Function*> keep_fns;

      for (auto &[f, ls] : map_fn_loops) {
        total_loops += ls.size();
        keep_fns.insert(f);
      }
      errs() << "Found " << total_loops << " outermost loops in " << keep_fns.size() << " functions" << "\n";

      for (auto &[f, ls] : map_fn_loops) {
        LoopInfo &LI = getAnalysis<LoopInfoWrapperPass>(*f).getLoopInfo();
        // if from a loop we can reach another function, remove from keep_fns
        for (BasicBlock* bb: ls) {
          auto l = LI.getLoopFor(bb);
          auto blocks = l->getBlocks();
          // errs() << "#Blocks to examine: " << blocks.size() << " in :" << l->getName() << (uint64_t)l<< '\n';
          for (BasicBlock* bb: blocks){
            BasicBlock &BB = *bb;

            // if is a function
            for (Instruction &I: BB) {
              if (CallBase* cs = dyn_cast<CallBase>(&I)) { 
                Function *f = cs->getCalledFunction();
                if (f) {
                  if (f->isDeclaration()) continue;
                  visitAndRemoveFnRec(f, visited_fns, keep_fns);
                }
              }
            }
          }
        }
      }

      unsigned int numLoops = 0;
      for (Function* f: keep_fns){
        numLoops += map_fn_loops[f].size();
      }

      errs() << numLoops << " outermost loops left in " << keep_fns.size() << " functions" << "\n";

      numLoops = 0;
      for (Function* f: keep_fns){
        auto &bbs = map_fn_loops[f];
        LoopInfo &LI = getAnalysis<LoopInfoWrapperPass>(*f).getLoopInfo();

        for (auto &bb : bbs) {
          auto l = LI.getLoopFor(bb);
          instrumentProf(l, numLoops, &M);
          ++numLoops;
        }
      }

      return true;
    }

    // This function is invoked once at the initialization phase of the compiler
    // The LLVM IR of functions isn't ready at this point
    bool doInitialization (Module &M) override {
      return false;
    }

    void getAnalysisUsage(AnalysisUsage &AU) const override {
      AU.addRequired<LoopInfoWrapperPass>();
    }
  };
}

// Next there is code to register your pass to "opt"
char OuterLoopProfInstr::ID = 0;
// INITIALIZE_PASS(OuterLoopProfInstr, "remove-bc", "Remove Bounds Checks", false, false)
static RegisterPass<OuterLoopProfInstr> X("outer-loop-prof-instr", "Instrument outer loop profile"); // only registers for opt tool

// Next there is code to register your pass to "clang"
/*static OuterLoopProfInstr * _PassMaker = NULL;
static RegisterStandardPasses _RegPass1(PassManagerBuilder::EP_OptimizerLast,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new OuterLoopProfInstr()); }}); // ** for -Ox
static RegisterStandardPasses _RegPass2(PassManagerBuilder::EP_EnabledOnOptLevel0,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new OuterLoopProfInstr()); }}); // ** for -O0
*/
