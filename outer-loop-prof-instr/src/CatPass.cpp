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
#include "llvm/IR/DebugInfoMetadata.h"

#include "llvm/Pass.h"
#include "llvm/PassSupport.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"

#include "GlobalCtors.h"

#include <iostream>
#include <fstream>
#include <set>
#include <vector>
#include <map>

using namespace llvm;

static cl::opt<unsigned> ExplorationDepth(
    "exp-depth", cl::init(0), cl::Hidden, cl::ZeroOrMore,
    cl::desc("Max depth of loop nest to profile"));
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

    bool hasBoundsCheck(Loop* l) {
      for (BasicBlock *bb: l->getBlocks()) {
        for (Instruction &I: *bb) {
          if (CallBase* cs = dyn_cast<CallBase>(&I)) {
            if (getFunctionName(cs).startswith("_ZN4core9panicking18panic_bounds_check")) {
              return true;

            }
          }
        }
      }

      return false;
    }

    void visitAndRemoveFnRec(Function* f, std::set<Function*> &visited_fns, std::set<Function*> &keep_fns, int depth) {
      // visited
      if (visited_fns.find(f) != visited_fns.end())
        return;

      // mark visited
      visited_fns.insert(f);

      // remove this from keep functions
      if (depth == 0)
        keep_fns.erase(f);
      else
        depth -= 1;

      for (BasicBlock &BB: *f){
        for (Instruction &I: BB) {
          if (CallBase* cs = dyn_cast<CallBase>(&I)) { 
            Function *f = cs->getCalledFunction();
            if (f) {
              if (f->isDeclaration()) continue;
              visitAndRemoveFnRec(f, visited_fns, keep_fns, depth);
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
            // // this check is not sound, could be a function call
            // if (!hasBoundsCheck(l))
            //   continue;
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
                Function *subf = cs->getCalledFunction();
                if (subf) {
                  if (subf->isDeclaration()) continue;

                  // for now, ignore top level function calls within bench
                  if (f->getName().startswith("bench")) {
                    cs->addAttribute(AttributeList::FunctionIndex, Attribute::NoInline);
                    visitAndRemoveFnRec(subf, visited_fns, keep_fns, ExplorationDepth + 1); 
                  }
                  else
                    visitAndRemoveFnRec(subf, visited_fns, keep_fns, ExplorationDepth);
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

      std::ofstream file("loops.txt");
      file << "#LoopID #Function #Loop" << std::endl;
      numLoops = 0;
      for (Function* f: keep_fns){
        auto &bbs = map_fn_loops[f];
        LoopInfo &LI = getAnalysis<LoopInfoWrapperPass>(*f).getLoopInfo();

        for (auto &bb : bbs) {
          auto l = LI.getLoopFor(bb);
          file << numLoops <<  " "  << f->getName().str() << " " << l->getName().str();
          auto &start = l->getLocRange().getStart();
          if (start) {
            auto *scope = dyn_cast<DIScope>(start->getScope());
            if (scope) {
              file << " " << scope->getFilename().str();
            }
            else {
              file << " <unknown_file>";
            }
            file << " " << start.getLine();
          }
          else {
            file << " <unknown_file> <unknown_line>";
          }

          file << std::endl;
          assert(l->getLoopDepth() == 1 && "loop depth has to be 1");
          instrumentProf(l, numLoops, &M);
          ++numLoops;
        }
      }
      file.close();

      // The initializer will register the file and dump profiled result
      FunctionCallee wrapper_InitFn =  M.getOrInsertFunction("outer_prof_init",
          Type::getVoidTy(M.getContext()),
          Type::getInt32Ty(M.getContext()));

      Constant *InitFn = cast<Constant>(wrapper_InitFn.getCallee());

      std::vector<Value*> Args(1);
      Args[0] = ConstantInt::get(Type::getInt32Ty(M.getContext()), numLoops, false);

      // Create the GlobalCtor function
      std::vector<Type*>FuncTy_0_args;
      FunctionType* FuncTy_0 = FunctionType::get(
          /*Result=*/Type::getVoidTy( M.getContext() ),
          /*Params=*/FuncTy_0_args,
          /*isVarArg=*/false);

      Function* func_initor = Function::Create(
          /*Type=*/FuncTy_0,
          /*Linkage=*/GlobalValue::ExternalLinkage,
          /*Name=*/"prof_initor", &M);

      BasicBlock *initor_entry = BasicBlock::Create(M.getContext(), "entry", func_initor,0);
      CallInst::Create(InitFn, Args, "", initor_entry);
      ReturnInst::Create(M.getContext(), initor_entry);

      // Function has been created, now add it to the global ctor list
      liberty::callBeforeMain(func_initor, 65535);

      if (numLoops > 0)
        return true;
      else
        return false;
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
