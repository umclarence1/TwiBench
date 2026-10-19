# Examples: whisper-small-ft on ood_test


## Hallucinations

- **REF:** Serug ba, Reu ba, Peleg ba, Eber ba, Sela ba,  
  **HYP:** Sɛro pa yɛ wo pɛle ba yɛbe yɛ bua yɛ yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua yɛ bua y�  
  WER 5.00

- **REF:** Metusela ba, Henok ba, Yared ba, Mahalaleel ba, Kainan ba, Lamek ba,  
  **HYP:** Mee tɔse number hɔ number yɛw number kɛ number number number  
  WER 1.00

- **REF:** Na ɔbonsam ka kyerɛɛ no sɛ: Wo na mede tumi yi nyinaa ne emu animuonyam bɛma woɔ;  
  **HYP:** Naobɔnsa mkɔkyɛw no se wo na me de me tɔ m'ani naa me mmo yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ  
  WER 3.59

- **REF:** Yɛnni biribiara sɛ paanoo nnum ne mpataa mmienu pɛ, gye sɛ yɛkɔtɔ aduane ma nkurɔfoɔ yi nyinaa.  
  **HYP:** Ne biribiara se pɛ number number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ number pɛ numb  
  WER 3.71

- **REF:** ɔno nso ho bɛyɛ Onipa Ba no aniwu ɛda a ɔde ɔno ne n’agya ne n’abɔfoɔ kronkron animuonyam bɛba no.  
  **HYP:** Noun so hɔbe yɛ wo nnepa bɛno a da wo deɛ no n'anea yɛ bubuo kɔm kɔm a na yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ number yɛ num  
  WER 2.90


## Highest WER (excluding hallucinations)

- **REF:** Melea ba, Mena ba, Matata ba, Natan ba, Dawid ba,  
  **HYP:** Mee yɛ pa, me yina pa, mataa tɔ pa, me tɔ number de wo yɛ hua  
  WER 1.60

- **REF:** Na ɛyɛɛ wɔn nyinaa ahodwiri, na wɔhyɛɛ Onyankopɔn animuonyam,  
  **HYP:** Na yɛ wo nyinaa aho dwoi naa wohyɛ wo yɛ kɔ pɔ nn me yɛ  
  WER 1.44

- **REF:** na ɔbɔɔ Onyankopɔn mpaeɛ anadwo mu no nyinaa.  
  **HYP:** Na obɔ nnkɔ pɔ m pa yɛ a na dwom n'ani na  
  WER 1.38

- **REF:** sɛ wɔbɛgye obi nkwa anaasɛ wɔbɛkum no?  
  **HYP:** Sɛ wo bɛkyɛ wo bɛn kɔa naa so wo bɛkɔ no  
  WER 1.29

- **REF:** togyefoɔ ne nnebɔneyɛfoɔ adamfo. Nanso nyansa mma nyinaa bu no bem.  
  **HYP:** To je fa ne nebɔ yɛfo adeɔfo no ase yɛw sɛn me n'a bubu no bɛm  
  WER 1.27


## Typical errors (WER near the median)

- **REF:** Mese wo sɛ: Sɔre fa wo kɛtɛ, na kɔ wo fie!  
  **HYP:** Me se wo se soro yɛ pɛ wo kɛte na kowɔfia  
  WER 0.91

- **REF:** Na ɔsee wɔn sɛ: Onipa ba no yɛ homeda so wura.  
  **HYP:** Na ɔse yɛwase yɛw number yɛw meda yɔ  
  WER 0.91

- **REF:** na wɔbɛhunuu onipa a ahonhommɔne firii ne mu kɔeɛ no sɛ ɔte Yesu nan ase fira ntoma a n’adwene mu ateɛ; na wɔsuroe.  
  **HYP:** Na wo behu no nnepaa a na m'onnwɔ nnwɔ meɛfɛ me mɔkɔa no  
  WER 0.91

- **REF:** ne wɔn a ahonhom fi ha wɔn; na ɔsaa wɔn yadeɛ.  
  **HYP:** Ne wo a naa huam huamɔfɛ huam naa wo soro yɛ de  
  WER 0.91

- **REF:** Na ɔka kyerɛɛ wɔn sɛ: Momma wɔn biribi nni! Na wɔse:  
  **HYP:** Na ɔkɔkyɛ wo nsae ma wo mbebi me  
  WER 0.91


## Perfect transcriptions

_none_
