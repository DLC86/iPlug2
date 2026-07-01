from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {path}, found {count}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


header = "IPlug/AUv2/IPlugAU.h"
replace_once(
    header,
    """  bool CheckLegalIO();
  void AssessInputConnections();

  UInt32 GetTagForNumChannels(int numChannels);""",
    """  bool CheckLegalIO();
  void AssessInputConnections();
  void SetPresentPreset(int presetNumber, const char* presetName);
  int GetPresentPresetNumber() const;
  const char* GetPresentPresetName() const;

  UInt32 GetTagForNumChannels(int numChannels);""",
)
replace_once(
    header,
    """  AudioTimeStamp mLastRenderTimeStamp;
  WDL_String mTrackName;
  template <class Plug, bool DoesMIDIIn>""",
    """  AudioTimeStamp mLastRenderTimeStamp;
  WDL_String mTrackName;
  bool mHasPresentPreset = false;
  int mPresentPresetNumber = -1;
  WDL_String mPresentPresetName;
  template <class Plug, bool DoesMIDIIn>""",
)


source = "IPlug/AUv2/IPlugAU.cpp"
replace_once(
    source,
    """OSStatus IPlugAU::GetState(CFPropertyListRef* ppPropList)
{""",
    """void IPlugAU::SetPresentPreset(int presetNumber, const char* presetName)
{
  mPresentPresetNumber = presetNumber;
  mPresentPresetName.Set(presetName ? presetName : "");
  mHasPresentPreset = true;
}

int IPlugAU::GetPresentPresetNumber() const
{
  return mHasPresentPreset ? mPresentPresetNumber : GetCurrentPresetIdx();
}

const char* IPlugAU::GetPresentPresetName() const
{
  return mHasPresentPreset ? mPresentPresetName.Get() : GetPresetName(GetCurrentPresetIdx());
}

OSStatus IPlugAU::GetState(CFPropertyListRef* ppPropList)
{""",
)
replace_once(
    source,
    """  PutStrInDict(pDict, kAUPresetNameKey, GetPresetName(GetCurrentPresetIdx()));""",
    """  PutStrInDict(pDict, kAUPresetNameKey, GetPresentPresetName());""",
)
replace_once(
    source,
    """  // ClassInfo may contain a host-assigned present-preset name rather than one
  // of the factory preset names. Retain it so a subsequent ClassInfo read
  // returns the same kAUPresetNameKey value, as required by auval.
  ModifyCurrentPreset(presetName);

  OnRestoreState();""",
    """  // ClassInfo may contain a host-assigned name that is not a factory preset.
  // Keep that metadata separate from the factory preset bank and return it on
  // subsequent PresentPreset and ClassInfo reads.
  SetPresentPreset(-1, presetName);

  OnRestoreState();""",
)
replace_once(
    source,
    """        AUPreset* pAUPreset = (AUPreset*) pData;
        pAUPreset->presetNumber = GetCurrentPresetIdx();
        const char* name = GetPresetName(pAUPreset->presetNumber);
        pAUPreset->presetName = CFStringCreateWithCString(0, name, kCFStringEncodingUTF8);""",
    """        AUPreset* pAUPreset = (AUPreset*) pData;
        pAUPreset->presetNumber = GetPresentPresetNumber();
        pAUPreset->presetName = CFStringCreateWithCString(0, GetPresentPresetName(), kCFStringEncodingUTF8);""",
)
replace_once(
    source,
    """    case kAudioUnitProperty_CurrentPreset:               // 28,
    case kAudioUnitProperty_PresentPreset:               // 36,
    {
      int presetIdx = ((AUPreset*) pData)->presetNumber;
      RestorePreset(presetIdx);
      return noErr;
    }""",
    """    case kAudioUnitProperty_CurrentPreset:               // 28,
    case kAudioUnitProperty_PresentPreset:               // 36,
    {
      const AUPreset* pAUPreset = (const AUPreset*) pData;
      const int presetIdx = pAUPreset->presetNumber;

      // A non-negative number recalls a factory preset. A negative number is
      // host-owned metadata for a custom state and must not alter DSP state.
      if (presetIdx >= 0 && !RestorePreset(presetIdx))
        return kAudioUnitErr_InvalidPropertyValue;

      if (pAUPreset->presetName)
      {
        CStrLocal presetName(pAUPreset->presetName);
        SetPresentPreset(presetIdx, presetName.Get());
      }
      else if (presetIdx >= 0)
      {
        SetPresentPreset(presetIdx, GetPresetName(presetIdx));
      }
      else
      {
        SetPresentPreset(presetIdx, "");
      }

      return noErr;
    }""",
)
replace_once(
    source,
    """void IPlugAU::InformHostOfPresetChange()
{
  //InformListeners(kAudioUnitProperty_CurrentPreset, kAudioUnitScope_Global);
  InformListeners(kAudioUnitProperty_PresentPreset, kAudioUnitScope_Global);
}""",
    """void IPlugAU::InformHostOfPresetChange()
{
  SetPresentPreset(GetCurrentPresetIdx(), GetPresetName(GetCurrentPresetIdx()));
  //InformListeners(kAudioUnitProperty_CurrentPreset, kAudioUnitScope_Global);
  InformListeners(kAudioUnitProperty_PresentPreset, kAudioUnitScope_Global);
}""",
)
