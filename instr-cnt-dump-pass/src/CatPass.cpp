#include "llvm/ADT/SmallVector.h"
#include "llvm/Analysis/BasicAliasAnalysis.h"
#include "llvm/Analysis/LoopPass.h"
#include "llvm/Analysis/Passes.h"
#include "llvm/Analysis/BlockFrequencyInfo.h"

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

#include <iostream>
#include <fstream>
#include <set>
#include <vector>
#include <map>

using namespace llvm;

namespace {

  struct InstrCountDump: public ModulePass{
    static char ID; 
    typedef std::map<std::pair<std::string, uint32_t>, std::array<uint32_t, 4>> MapIDStat_t;
    
    static StringRef getFunctionName(CallBase *call) {
        Function *fun = call->getCalledFunction();
        if (fun) // thanks @Anton Korobeynikov
            return fun->getName(); // inherited from llvm::Value
        else
            return StringRef("");
    }

    InstrCountDump() : ModulePass(ID) {}

    unsigned long getInstDynCount(const Instruction *inst) {
      // edge-count profile results
      // ProfileInfo &pi = getAnalysis< ProfileInfo >();

      const BasicBlock *bb = inst->getParent();
      const Function *fcn = bb->getParent();

      // Evil, but okay because it won't modify the IR
      Function *non_const_fcn = const_cast<Function *>(fcn);
      BlockFrequencyInfo &bfi =
        getAnalysis<BlockFrequencyInfoWrapperPass>(*non_const_fcn).getBFI();

      auto fcnt = fcn->getEntryCount();
      if ((fcnt.hasValue() && fcnt.getCount() < 1) || !fcnt.hasValue()) {
        // Function never executed or no profile info available, so we don't know
        // the relative weights of the blocks inside.  We will assign the same
        // relative weight to all blocks in this function.

        return 0;
      } else {
        // sot
        // const double bbcnt = pi.getExecutionCount(bb);
        if (!bfi.getBlockProfileCount(bb).hasValue()) {
          errs() << "No profile count for BB " << bb->getName() << "\n";
          return 0; 
        }
        const double bbcnt = bfi.getBlockProfileCount(bb).getValue();
        const unsigned long bbicnt = (unsigned long)(bbcnt);

        // errs() << "bbcnt, bbicnt: " << bbcnt << " " << bbicnt << "\n";

        return bbicnt;
      }
    }

    bool registerCnt(Instruction &I, MapIDStat_t &m) {
      bool isGep = (dyn_cast<GetElementPtrInst>(&I) != NULL);

      MDNode *md; 
      if (isGep) {
        char name[] = "GepID";
        md = I.getMetadata(name);
      } else {
        char name[] = "bcbrID";
        md = I.getMetadata(name);
      }

      if (md == NULL)
        return false;

      errs() << "Found MD\n";

      MDString *MDS = dyn_cast<MDString> (md->getOperand(0));
      if (!MDS)
        return false;

      std::string str = MDS->getString().str();
      // unique ID
      ValueAsMetadata *vID= dyn_cast<ValueAsMetadata> (md->getOperand(1));
      ConstantInt *CI = cast< ConstantInt >( vID->getValue()  );
      uint64_t id = CI->getValue().getZExtValue();

      auto key = make_pair(str, id);

      auto instCnt = getInstDynCount(&I);
      
      // create entry if does not exist
      if (m.find(key) == m.end()) {
        m[key] = {0, 0, 0, 0};
      }

      // static count ++
      // dynamic count += instCnt
      if (isGep) {
        m[key][0] += 1;
        m[key][1] += instCnt;
      } else {
        m[key][2] += 1;
        m[key][3] += instCnt;
      }

      return true;
    }

    // 1. Need to run loopssa pass before
    // 2. Iterate all loops, check the depth, if is outermost loop, put in a list
    // 3. Go through all loops, find all functions called, remove them from the keep_fns set
    bool runOnModule(Module& M){

      // map from <string, u32> to array<unsigned long, 4>
      MapIDStat_t map_id_stat;

      for (auto IF = M.begin(), E = M.end(); IF != E; ++IF) {
        Function &F = *IF;
        if (F.isDeclaration()) continue;
        if (F.size() == 0) continue;  // not sure if this is necessary

        for (BasicBlock &bb: F) {
          for (Instruction &I: bb) {
            // check each instruction
            if (dyn_cast<BranchInst>(&I) || dyn_cast<GetElementPtrInst>(&I)) {
              registerCnt(I, map_id_stat);
            }
          }
        }
      }

      // print the map into json
      std::ofstream file("cnts.txt");
      file << "{\n";
      for (auto &[k, v] : map_id_stat){
        auto &[str, id] = k;
        auto &[gep_st, gep_dyn, br_st, br_dyn] = v;

        file << "\"" << str << "-" << id << "\": ["
          << gep_st << ", " << gep_dyn << ", " << br_st
          << ", " << br_dyn << "], \n";
      }
      file << "}";
      file.close();

      return false;
    }

    // This function is invoked once at the initialization phase of the compiler
    // The LLVM IR of functions isn't ready at this point
    bool doInitialization (Module &M) override {
      return false;
    }

    void getAnalysisUsage(AnalysisUsage &AU) const override {
      AU.addRequired< BlockFrequencyInfoWrapperPass >();
    }
  };
}

// Next there is code to register your pass to "opt"
char InstrCountDump::ID = 0;
// INITIALIZE_PASS(InstrCountDump, "remove-bc", "Remove Bounds Checks", false, false)
static RegisterPass<InstrCountDump> X("instr-cnt-dump", "Dump the instruction count based on edge prof"); // only registers for opt tool

// Next there is code to register your pass to "clang"
/*static InstrCountDump * _PassMaker = NULL;
static RegisterStandardPasses _RegPass1(PassManagerBuilder::EP_OptimizerLast,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new InstrCountDump()); }}); // ** for -Ox
static RegisterStandardPasses _RegPass2(PassManagerBuilder::EP_EnabledOnOptLevel0,
    [](const PassManagerBuilder&, legacy::PassManagerBase& PM) {
        if(!_PassMaker){ PM.add(_PassMaker = new InstrCountDump()); }}); // ** for -O0
*/
