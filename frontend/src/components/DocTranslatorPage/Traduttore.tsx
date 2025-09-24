// // import { useTheme } from '@mui/material/styles'
// import { Box, Button } from '@mui/material'
// import { useState, useEffect } from 'react'
// import UploadableTextArea from '../upload-components/UploadableTextArea'
// import DocumentList from '../upload-components/DocumentListUploaded';
// import { api } from '../../api/api'
// import CircularProgress from '@mui/material/CircularProgress';
// import LinedDropdown from '../dropdowns/LinedDropdown';
// import { toast } from 'react-toastify'

// interface Document {
//   id: number;
//   name: string;
//   type: string;
//   translatedUrl?: string;
// }

// const languageMap: Record<string, string> = {
//   'Italiano': 'italian',
//   'Inglese': 'english',
//   'Francese': 'french',
//   'Spagnolo': 'spanish',
//   'Greco': 'greek',
//   'Portoghese': 'portuguese',
//   'Tedesco': 'german',
// };

// const Traduttore = () => {
//   // const theme = useTheme()
//   const [isLoading, setIsLoading] = useState<boolean>(false);
  
//   // Files
//   const [files, setFiles] = useState<File[]>([]);
//   const [isFileTranslated, setIsFileTranslated] = useState<boolean>(false);
//   const [documentsTranslated, setDocumentsTranslated] = useState<Document[]>([]);
  
//   // Languages
//   const [selectedLanguageOriginal, setSelectedLanguageOriginal] = useState<string | string[]>('');
//   const [selectedLanguageTarget, setSelectedLanguageTarget] = useState<string | string[]>('');
//   const [filteredOriginalLanguages, setFilteredOriginalLanguages] = useState<string[]>([]);
//   const [filteredTargetLanguages, setFilteredTargetLanguages] = useState<string[]>([]);
//   const languages = ['Italiano', 'Inglese', 'Francese', 'Spagnolo', 'Greco', 'Portoghese', 'Tedesco'];
  
//   useEffect(() => {
//     setFilteredOriginalLanguages(languages.filter(lang => lang !== selectedLanguageTarget));
//     setFilteredTargetLanguages(languages.filter(lang => lang !== selectedLanguageOriginal));
//   }, [selectedLanguageOriginal, selectedLanguageTarget]);

//   // Send Button Activation
//   const isButtonEnabled =
//     selectedLanguageOriginal !== '' && selectedLanguageTarget !== '' && files.length > 0;


//   // File Delete 
//   const handleDeleteDocument = (id: number) => {
//     setDocumentsTranslated((prevDocs) => prevDocs.filter((doc) => doc.id !== id));
//     if (documentsTranslated.length === 0) {
//       setIsFileTranslated(false);
//     }
//   };

//   // File Upload
//   const handleFileUpload = (file: File | File[]) => {
//     setFiles(prevFiles => [
//       ...prevFiles,
//       ...(Array.isArray(file) ? file : [file])
//     ]);
//   };

//   // File Extension
//   const getFileExtension = (filename: string) => {
//     return filename.substring(filename.lastIndexOf('.') + 1, filename.length);
//   };

//   const handleNewTranslation = () => {
//     setIsFileTranslated(false);
//     setDocumentsTranslated([]);
//     setFiles([]);
//     setSelectedLanguageOriginal('');
//     setSelectedLanguageTarget('');
//   }

//   // Translation
//   const handleTranslation = async () => {
//     if (!selectedLanguageOriginal || !selectedLanguageTarget) {
//       return;
//     }

//     setIsLoading(true); 
//     try {

//       const translationRequests = files.map(file => {
//         const formData = new FormData();
//         formData.append('file', file);
//         formData.append('origin', languageMap[selectedLanguageOriginal! as string]);
//         formData.append('target', languageMap[selectedLanguageTarget! as string]);

//         return api.post('/deepl/file/', formData, {
//           headers: { "Content-Type": "multipart/form-data" }
//         });
//       });

//       const responses = await Promise.all(translationRequests);
      
//       const translatedDocuments: Document[] = responses.map((res, idx) => {
//         const translatedFileUrl = `/deepl/file?document=${res.data.document}`;
//         const translatedFileName = res.data.document || files[idx].name;
//         const fileExtension = getFileExtension(translatedFileName);

//         return {
//           id: Date.now() + idx,
//           name: translatedFileName,
//           type: fileExtension,
//           translatedUrl: translatedFileUrl,
//         };
//       });

//       setDocumentsTranslated(prevDocs => [...prevDocs, ...translatedDocuments]);
//       setIsFileTranslated(true);
//       setFiles([]);
//       setIsLoading(false);

//     } catch (error) {
//       const msg = error instanceof Error ? error.message : String(error);
//       toast.error(`Error Translating Document: ${msg}`);
//       setIsLoading(false);
//     }
    
//   };


//   return (
//     <Box sx={{ display: 'flex', flexDirection: 'column', marginTop: '2vw', alignItems: 'center' }}>

//       <Box
//         sx={{
//           display: 'flex',
//           flexDirection: 'row',
//           gap: '2vw',
//           width: '100%',
//           height: '60vh',
//         }}
//       >

//         <Box sx={{ display:'flex', flexDirection:'column', gap:1.5, alignItems:'center', justifyContent:'center', width:'100%', height:'100%' }}>
//           {isFileTranslated ? (
//             <>
//               <DocumentList documents={[...documentsTranslated].reverse()} onDelete={handleDeleteDocument} isResult={true} isTranslation={true} />
//               <Button
//                 variant="outlined"
//                 color="primary"
//                 onClick={handleNewTranslation}
//                 sx={{ width: 250 }}
//               >
//                 Traduci un nuovo documento
//               </Button>
//             </>
//           ) : (
//             <>
//               <UploadableTextArea onFileUpload={handleFileUpload} documentPlaceHolder='Carica un file o trascinalo qui'/>
//               <LinedDropdown
//                 title="Lingua originale del documento"
//                 options={filteredOriginalLanguages}
//                 value={selectedLanguageOriginal}
//                 onChange={setSelectedLanguageOriginal}
//                 width={300}
//               />
//               <LinedDropdown
//                 title="Lingua del documento tradotto"
//                 options={filteredTargetLanguages}
//                 value={selectedLanguageTarget}
//                 onChange={setSelectedLanguageTarget}
//                 width={300}
//               />
              
//               <Button
//                 variant="contained"
//                 color="primary"
//                 disabled={!isButtonEnabled || isLoading}
//                 onClick={handleTranslation}
//                 sx={{ width: 'calc(9.5vw)' }}
//               >
//                 {isLoading ? <CircularProgress size={24} color="inherit" /> : 'Traduci'}
//               </Button>
//             </>
//           )

//           }
//         </Box>
          
//       </Box>

//     </Box>
    
//   )
// }

// export default Traduttore
