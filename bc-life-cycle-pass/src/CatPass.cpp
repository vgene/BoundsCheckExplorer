#include "MarkBCGEP.h"
#include "llvm/ADT/ArrayRef.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Metadata.h"
#include "llvm/PassSupport.h"
#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/CFG.h"
#include "llvm/Support/Casting.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Analysis/BasicAliasAnalysis.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include <cstdint>
#include <fstream>

#include <set>
#include <string>

using namespace llvm;


namespace {

  struct MarkBCGEP : public FunctionPass {
    static char ID; 
    
    static StringRef getFunctionName(CallBase *call) {
        Function *fun = call->getCalledFunction();
        if (fun) // thanks @Anton Korobeynikov
            return fun->getName(); // inherited from llvm::Value
        else
            return StringRef("indirect call");
    }

    static bool isBoundsCheck(CallBase *call) {
      auto name = getFunctionName(call);
      if (name.startswith("_ZN4core9panicking18panic_bounds_check")) {
         //  || name.startswith("_ZN4core5slice22slice_index_order_fail")
         //  || name.startswith("_ZN4core5slice20slice_index_len_fail") ) {
        return true;
      }
      else {
        return false;
      }
    }

    // set the metadata for branches
    static void setBcBrMetadata(LLVMContext &C, Instruction *inst, std::string fn_name, uint64_t uniqueID) {
      ConstantInt *uniqueIDv = ConstantInt::get(Type::getInt32Ty(C), uniqueID);
      Metadata *md = ValueAsMetadata::get(uniqueIDv);
      MDString *fcnname = MDString::get(C, fn_name);

      Metadata *values[] = { fcnname, md};

      MDNode* mdNode = MDNode::get(C, values);
      char name[]="bcbrID";

      inst->setMetadata(name, mdNode);
    }

    // set the metadata for branches
    static void setGepMetadata(LLVMContext &C, Instruction *inst, std::string fn_name, uint64_t uniqueID) {
      ConstantInt *uniqueIDv = ConstantInt::get(Type::getInt32Ty(C), uniqueID);
      Metadata *md = ValueAsMetadata::get(uniqueIDv);
      MDString *fcnname = MDString::get(C, fn_name);

      Metadata *values[] = { fcnname, md};

      MDNode* mdNode = MDNode::get(C, values);
      char name[]="GepID";

      inst->setMetadata(name, mdNode);
    }

    MarkBCGEP() : FunctionPass(ID) {}

    // This function is invoked once at the initialization phase of the compiler
    // The LLVM IR of functions isn't ready at this point
    bool doInitialization (Module &M) override {
      return false;
    }

    // This function is invoked once per function compiled
    // The LLVM IR of the input functions is ready and it can be analyzed and/or transformed
    bool runOnFunction (Function &F) override {
      std::string fn_name = F.getName().str();

      std::ifstream file("fn_rm.txt");
      if (!file.fail()) {
        // file exist, only remove bc from this file
        std::set<std::string> s;
        std::string str;

        while (file >> str) {
          s.insert(str);
        }

        if (s.find(fn_name) == s.end())
          return false;
      }

      // for each bounds check block
      // find the branch instruction, and mark it with an unique id
      // also mark the GEP instruction that the bc protected with the same ID
      LLVMContext &C = F.getContext();
      uint64_t uniqueID = 0;


      unsigned long bc_num = 0;
      // typedef std::pair<BasicBlock*, uint64_t> edge;
      // std::vector<edge> toMark;
      for (BasicBlock &bb: F) {
        BasicBlock* succ;
        for (Instruction &I: bb) {
          if (CallBase* cs = dyn_cast<CallBase>(&I)) {
            if (isBoundsCheck(cs)) {

              bc_num++;
              // get predecessor of the basic block
              // get the last branch inst of the predecessor
              // create a branch to the othe
              for (BasicBlock* pred: predecessors(&bb)) { // maybe our unlinking invalidates some of these preds?
                // found bounds check
                Instruction *term = pred->getTerminator();
                int numSucc = term->getNumSuccessors();
                if (numSucc == 2) { // one is bb, one is the original next block

                  setBcBrMetadata(C, term, fn_name, uniqueID);
                  /*
                  // for all the PHINode, remove the incoming edge
                  for (PHINode &PHI: bb.phis()) {
                    PHI.removeIncomingValue(pred, false); // don't delete phi if empty, will screw up the iterator
                  }
                  */

                  if (term->getSuccessor(0) == &bb) {
                    succ = term->getSuccessor(1);
                  } else {
                    succ = term->getSuccessor(0);
                  }

                  // go to succ and mark the first GEPsucc
                  bool hasGep = false;
                  for (Instruction &newI: *succ) {
                    if (GetElementPtrInst *gep = dyn_cast<GetElementPtrInst>(&newI)) {
                      setGepMetadata(C, gep, fn_name, uniqueID);
                      hasGep = true;
                      break;
                    }
                  }

                  if (!hasGep) {
                    errs() << "No GEP for #" << uniqueID << " bc in function " << fn_name << '\n';
                    // print source code location
                    auto &debugLoc = I.getDebugLoc();
                    if (debugLoc) {
                      errs() << "  ";
                      auto *scope = dyn_cast<DIScope>(debugLoc->getScope());
                      if (scope) {
                        errs() << scope->getFilename() << " ";
                      }
                      errs() << "(" << debugLoc.getLine() << ", " << debugLoc.getCol() << ")\n";
                    }
                  }

                  ++uniqueID;
                  // BranchInst::Create(succ, term);
                  // term->eraseFromParent();
                } else if (numSucc == 1) { // may be leading to a landing pad, so iteratively go up until conditional branch to panic_bounds_check
                  errs() << "only one successor in the previous block\n";
                } else {
                  // one should be the bounds check
                  // toRemove.push_back(edge(term, &bb));
                  errs() << "more than two successors in the previous block\n";
                }
              }
            }
          }
        }
      }

      /*
      for (auto &i : toRemove){
        auto term = i.first;
        auto succ = i.second;
        if (term->getNumSuccessors() == 2) {
          BranchInst::Create(succ, term);
          term->eraseFromParent();
        }
        else if (term->getNumSuccessors() > 2) {
          // CAUTION: this case is not succ, but bb!!
          SwitchInst* sw = dyn_cast<SwitchInst>(term);

          if (!sw){
            errs() << "multiple destination but not switch\n";
          }
          else {
            auto *val = sw->findCaseDest(succ);
            if (!val) {
              errs() << "Couldn't find the destination in multiple destination case\n";
            }
            else {
              SwitchInst::CaseIt it = sw->findCaseValue(val);
              sw->removeCase(it);
            }
          }
        }
        else {
          assert(false && "successor should be no less than 2");
        }

      }
      */
      // if (bc_num > 0) {
      //   errs() << "Found function in list: " << fn_name << '\n';
      //   errs() << "  Bounds check removed: " << bc_num << '\n';
      // }
      return true;
    }

    void getAnalysisUsage(AnalysisUsage &AU) const override {}
  };
}

PreservedAnalyses MarkBCGEPPass::run(Function &F, FunctionAnalysisManager &AM) {
  PreservedAnalyses PA;
  PA.preserve<BasicAA>();
  return PA;
}

// Next there is code to register your pass to "opt"
char MarkBCGEP::ID = 0;
static RegisterPass<MarkBCGEP> X("mark-bc-gep", "Mark the GEP instructions protected by the bounds check"); // only registers for opt tool

Pass *llvm::createMarkBCGEPPass() { 
        return new MarkBCGEP();
}

// Next there is code to register your pass to "clang"
/*static MarkBCGEP * _PassMaker = NULL;
static RegisterStandardPasses _RegPass1(PassManagerBuilder::EP_OptimizerLast,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new MarkBCGEP()); }}); // ** for -Ox
static RegisterStandardPasses _RegPass2(PassManagerBuilder::EP_EnabledOnOptLevel0,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new MarkBCGEP()); }}); // ** for -O0
*/
