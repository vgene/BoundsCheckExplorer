#include "RemoveBoundsChecks.h"
//#include "llvm/PassSupport.h"
#include "llvm/IR/Instruction.h"
#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Intrinsics.h"
#include "llvm/IR/CFG.h"
#include "llvm/Support/Casting.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Analysis/BasicAliasAnalysis.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include <fstream>

#include <set>
#include <tuple>
#include <optional>

using namespace llvm;

namespace {

  struct RemoveBoundsChecks : public FunctionPass {
    static char ID;

    static StringRef getFunctionName(CallBase *call) {
        Function *fun = call->getCalledFunction();
        if (fun) // thanks @Anton Korobeynikov
            return fun->getName(); // inherited from llvm::Value
        else
            return StringRef("indirect call");
    }

    RemoveBoundsChecks() : FunctionPass(ID) {}

    // This function is invoked once at the initialization phase of the compiler
    // The LLVM IR of functions isn't ready at this point
    bool doInitialization (Module &M) override {
      return false;
    }

    typedef std::tuple<unsigned, unsigned, std::string> DebugLoc;
    // parse from the debug info
    std::optional<std::set<DebugLoc>> parseFromDebug(std::string filename) {
      std::ifstream file(filename);

      std::set<DebugLoc> debugLines;

      // assuming the file format: line column filename on each line
      if (!file.fail()) {
        int line, column;
        std::string srcFile;
        while (file >> line >> column >> srcFile) {
          //debugLines.insert(std::make_tuple(line, column, srcFile));
          debugLines.insert(std::make_tuple(line, 0, srcFile));
        }
      }
      else {
	return std::nullopt;
      }

      return debugLines;
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


      bool onlyDebugLocs = false;
      std::set<DebugLoc> debugLocs;
      auto filename = "bc_loc.txt";
      auto ret = parseFromDebug(filename);
      if (ret.has_value()) {
        debugLocs = *ret;
        onlyDebugLocs = true;
      }

      unsigned long bc_num = 0;
      typedef std::pair<Instruction*, BasicBlock*> edge;
      std::vector<edge> toRemove;
      for (BasicBlock &bb: F) {
        BasicBlock* succ;
        for (Instruction &I: bb) {
          if (CallBase* cs = dyn_cast<CallBase>(&I)) {
            if (getFunctionName(cs).startswith("_ZN4core9panicking18panic_bounds_check")
                || getFunctionName(cs).startswith("_ZN4core5slice22slice_index_order_fail")
                || getFunctionName(cs).startswith("_ZN4core5slice20slice_index_len_fail")
                || getFunctionName(cs).startswith("_ZN4core5slice24slice_end_index_len_fail")
                ) {

              auto &debugLoc = I.getDebugLoc();
              if (onlyDebugLocs) {
                if (!debugLoc)
                  continue;

                auto *scope = dyn_cast<DIScope>(debugLoc->getScope());
                if (!scope) {
                  continue;
                }

                std::string bcFile = scope->getFilename().str();
                unsigned line = debugLoc.getLine();
                unsigned column = debugLoc.getCol();

                //auto tu = std::make_tuple(line, column, bcFile);
                auto tu = std::make_tuple(line, 0, bcFile);
                if (debugLocs.find(tu) == debugLocs.end())
                  continue;
              }

              if (debugLoc) {
                errs() << "  ";
                auto *scope = dyn_cast<DIScope>(debugLoc->getScope());
                if (scope) {
                  errs() << scope->getFilename() << " ";
                }
                errs() << "(" << debugLoc.getLine() << ", " << debugLoc.getCol() << ")\n";
              }


              bc_num++;
              // bad b/c we may be changing the semantics of the program
              /*
              if (InvokeInst* ii = dyn_cast<InvokeInst>(&I)) {
                errs() << "panic_bounds_check INVOKED\n";
              } else {
                errs() << "panic_bounds_check CALLED\n";
              }
              */
              // get predecessor of the basic block
              // get the last branch inst of the predecessor
              // create a branch to the othe
              for (BasicBlock* pred: predecessors(&bb)) { // maybe our unlinking invalidates some of these preds?
                // found bounds check
                Instruction *term = pred->getTerminator();
                int numSucc = term->getNumSuccessors();
                if (numSucc == 2) { // one is bb, one is the original next block

                  // for all the PHINode, remove the incoming edge
                  for (PHINode &PHI: bb.phis()) {
                    PHI.removeIncomingValue(pred, false); // don't delete phi if empty, will screw up the iterator
                  }

                  if (term->getSuccessor(0) == &bb) {
                    succ = term->getSuccessor(1);
                  } else {
                    succ = term->getSuccessor(0);
                  }
                  toRemove.push_back(edge(term, succ)); // log it in the vector
                  // BranchInst::Create(succ, term);
                  // term->eraseFromParent();
                } else if (numSucc == 1) { // may be leading to a landing pad, so iteratively go up until conditional branch to panic_bounds_check
                  errs() << "only one successor in the previous block\n";
                } else {
                  // one should be the bounds check
                  toRemove.push_back(edge(term, &bb));
                  //errs() << "more than two successors in the previous block\n";
                }
              }
            }
          }
        }
      }

      for (auto &i : toRemove){
        auto term = i.first;
        auto succ = i.second;
        if (term->getNumSuccessors() == 2) {
          BranchInst* br = dyn_cast<BranchInst>(term);
          if (!br) {
            errs() << "two destinations but not branch\n";
            continue;
          }

          //Value* condition;
          //if (term->getSuccessor(0) == succ) {
            //condition = br->getCondition();
          //} else {
            //condition = br->getCondition();
            //condition = BinaryOperator::CreateNot(condition, "", term);
          //}

          //// create assume
          //Function *FnAssume = Intrinsic::getDeclaration(F.getParent(), Intrinsic::assume);
          //CallInst *call = CallInst::Create(FnAssume, {condition}, "", term);

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

              //Value* condition;
              //condition = sw->getCondition();
              //condition = CmpInst::Create(Instruction::ICmp, llvm::CmpInst::ICMP_NE, condition, val, "", term);

              //// create assume
              //Function *FnAssume = Intrinsic::getDeclaration(F.getParent(), Intrinsic::assume);
              //CallInst *call = CallInst::Create(FnAssume, {condition}, "", term);

              sw->removeCase(it);
            }
          }
        }
        else {
          assert(false && "successor should be no less than 2");
        }

      }
      if (bc_num > 0) {
        errs() << "Found function in list: " << fn_name << '\n';
        errs() << "  Bounds check removed: " << bc_num << '\n';
      }
      return true;
    }

    void getAnalysisUsage(AnalysisUsage &AU) const override {}
  };
}

PreservedAnalyses RemoveBoundsChecksPass::run(Function &F, FunctionAnalysisManager &AM) {
  PreservedAnalyses PA;
  PA.preserve<BasicAA>();
  return PA;
}

// Next there is code to register your pass to "opt"
char RemoveBoundsChecks::ID = 0;
// INITIALIZE_PASS(RemoveBoundsChecks, "remove-bc", "Remove Bounds Checks", false, false)
static RegisterPass<RemoveBoundsChecks> X("remove-bc", "Remove Bounds Checks"); // only registers for opt tool

Pass *llvm::createRemoveBoundsChecksPass() {
        return new RemoveBoundsChecks();
}

// Next there is code to register your pass to "clang"
/*static RemoveBoundsChecks * _PassMaker = NULL;
static RegisterStandardPasses _RegPass1(PassManagerBuilder::EP_OptimizerLast,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new RemoveBoundsChecks()); }}); // ** for -Ox
static RegisterStandardPasses _RegPass2(PassManagerBuilder::EP_EnabledOnOptLevel0,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new RemoveBoundsChecks()); }}); // ** for -O0
*/
