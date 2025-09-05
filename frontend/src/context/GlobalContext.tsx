// GlobalContext.tsx
import React, { createContext, useContext, useState  } from "react";

// API
// import { fetchCompanyInfo } from "../api/companyInfo"; 

// Interfaces
// import type { CompanyInfoAdm } from "../interfaces/companyInfoInterface";
import { GlobalContextType, AwaitingDeepResponseType } from "../interfaces/globalContext";

// Hooks
import { useDeepPolling } from "../hooks/useDeepPolling";

const GlobalContext = createContext<GlobalContextType | undefined>(undefined);

export const GlobalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // const [companyInfoAdm, setCompanyInfoAdm] = useState<CompanyInfoAdm | null>(null);
  const [awaitingDeepResponse, setAwaitingDeepResponse] = useState<AwaitingDeepResponseType | null>(null);
  const [selectedLawTab, setSelectedLawTab] = useState<string | null>(null);

  // useEffect(() => {
  //   fetchCompanyInfo().then(setCompanyInfoAdm);
  // }, []);

  // Polling para Deep Research
  useDeepPolling(awaitingDeepResponse, setAwaitingDeepResponse);

  return (
    <GlobalContext.Provider value={{
      // companyInfoAdm, 
      awaitingDeepResponse, 
      setAwaitingDeepResponse,
      selectedLawTab,
      setSelectedLawTab
    }}>
      {children}
    </GlobalContext.Provider>
  );
};

export function useGlobal() {
  const ctx = useContext(GlobalContext);
  if (!ctx) throw new Error("useGlobal must be used inside GlobalProvider");
  return ctx;
}