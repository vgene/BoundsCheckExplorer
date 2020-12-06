#include "llvm/PassSupport.h"
#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/CFG.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Analysis/BasicAliasAnalysis.h"
#include <iostream>

#include <set>

using namespace llvm;

namespace {

  struct ShowBCFuncName: public FunctionPass {
    static char ID; 
    
    static StringRef getFunctionName(CallBase *call) {
        Function *fun = call->getCalledFunction();
        if (fun) // thanks @Anton Korobeynikov
            return fun->getName(); // inherited from llvm::Value
        else
            return StringRef("");
    }

    ShowBCFuncName() : FunctionPass(ID) {}

    // This function is invoked once at the initialization phase of the compiler
    // The LLVM IR of functions isn't ready at this point
    bool doInitialization (Module &M) override {
      return false;
    }

    // This function is invoked once per function compiled
    // The LLVM IR of the input functions is ready and it can be analyzed and/or transformed
    bool runOnFunction (Function &F) override {
      for (BasicBlock &bb: F) {
        BasicBlock* succ;
        for (Instruction &I: bb) {
          if (CallBase* cs = dyn_cast<CallBase>(&I)) {
            if (getFunctionName(cs).startswith("_ZN4core9panicking18panic_bounds_check")
                || getFunctionName(cs).startswith("_ZN4core5slice22slice_index_order_fail")
                || getFunctionName(cs).startswith("_ZN4core5slice20slice_index_len_fail")
                ) {
              std::cout << F.getName().str() << std::endl;
              return false;
            }
          }
        }
      }

      return false;
    }

    void getAnalysisUsage(AnalysisUsage &AU) const override {}
  };
}

// Next there is code to register your pass to "opt"
char ShowBCFuncName::ID = 0;
// INITIALIZE_PASS(ShowBCFuncName, "remove-bc", "Remove Bounds Checks", false, false)
static RegisterPass<ShowBCFuncName> X("show-bc-names", "Show all function names with bc"); // only registers for opt tool

// Next there is code to register your pass to "clang"
/*static ShowBCFuncName * _PassMaker = NULL;
static RegisterStandardPasses _RegPass1(PassManagerBuilder::EP_OptimizerLast,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new ShowBCFuncName()); }}); // ** for -Ox
static RegisterStandardPasses _RegPass2(PassManagerBuilder::EP_EnabledOnOptLevel0,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new ShowBCFuncName()); }}); // ** for -O0
*/
