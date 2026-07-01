from pathlib import Path
import re


def read(path: str) -> str:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return f.read()


def write(path: str, text: str) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    pattern = re.compile(r"\r?\n".join(re.escape(line) for line in old.split("\n")))
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {label} block, found {len(matches)}")
    match = matches[0]
    newline = "\r\n" if "\r\n" in match.group(0) else "\n"
    return text[:match.start()] + new.replace("\n", newline) + text[match.end():]


def replace_regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    matches = list(re.finditer(pattern, text, flags=re.S))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {label} block, found {len(matches)}")
    match = matches[0]
    newline = "\r\n" if "\r\n" in match.group(0) else "\n"
    return text[:match.start()] + replacement.replace("\n", newline) + text[match.end():]


host_h_path = "IPlug/APP/IPlugAPP_host.h"
host_h = read(host_h_path)
host_h = replace_once(
    host_h,
    """    , mAudioInChanL(obj.mAudioInChanL)
    , mAudioInChanR(obj.mAudioInChanR)
    , mAudioOutChanL(obj.mAudioInChanL)
    , mAudioOutChanR(obj.mAudioInChanR)""",
    """    , mAudioInChanL(obj.mAudioInChanL)
    , mAudioInChanR(obj.mAudioInChanR)
    , mAudioOutChanL(obj.mAudioOutChanL)
    , mAudioOutChanR(obj.mAudioOutChanR)""",
    "AppState output-channel copy",
)
write(host_h_path, host_h)


host_cpp_path = "IPlug/APP/IPlugAPP_host.cpp"
host_cpp = read(host_cpp_path)
host_cpp = replace_once(
    host_cpp,
    '      mINIPath.Append("\\\\settings.ini");',
    '      mINIPath.Append("settings.ini");',
    "macOS settings path",
)

new_init_audio = r'''bool IPlugAPPHost::InitAudio(uint32_t inId, uint32_t outId, uint32_t sr, uint32_t iovs)
{
  CloseAudio();

  RtAudio::StreamParameters iParams, oParams;
  const int nInputChannels = GetPlug()->MaxNChannels(ERoute::kInput);
  const int nOutputChannels = GetPlug()->MaxNChannels(ERoute::kOutput);
  const RtAudio::DeviceInfo inputInfo = mDAC->getDeviceInfo(inId);
  const RtAudio::DeviceInfo outputInfo = mDAC->getDeviceInfo(outId);

  if ((nInputChannels > 0 && inputInfo.inputChannels < static_cast<unsigned int>(nInputChannels))
      || (nOutputChannels > 0 && outputInfo.outputChannels < static_cast<unsigned int>(nOutputChannels)))
  {
    MessageBox(gHWND,
               "The selected audio device does not provide enough input or output channels.",
               "Error",
               MB_OK);
    return false;
  }

  auto ClampFirstChannel = [](uint32_t selectedOneBased, int requiredChannels, unsigned int availableChannels) {
    if (requiredChannels <= 0 || availableChannels <= static_cast<unsigned int>(requiredChannels))
      return 0u;

    const unsigned int requested = selectedOneBased > 0 ? selectedOneBased - 1 : 0;
    const unsigned int maxFirst = availableChannels - static_cast<unsigned int>(requiredChannels);
    return requested < maxFirst ? requested : maxFirst;
  };

  iParams.deviceId = inId;
  iParams.nChannels = nInputChannels;
  iParams.firstChannel = ClampFirstChannel(mState.mAudioInChanL, nInputChannels, inputInfo.inputChannels);

  oParams.deviceId = outId;
  oParams.nChannels = nOutputChannels;
  oParams.firstChannel = ClampFirstChannel(mState.mAudioOutChanL, nOutputChannels, outputInfo.outputChannels);

  if (nInputChannels > 0)
  {
    mState.mAudioInChanL = iParams.firstChannel + 1;
    mState.mAudioInChanR = iParams.firstChannel + static_cast<unsigned int>(nInputChannels);
  }

  if (nOutputChannels > 0)
  {
    mState.mAudioOutChanL = oParams.firstChannel + 1;
    mState.mAudioOutChanR = oParams.firstChannel + static_cast<unsigned int>(nOutputChannels);
  }

  mBufferSize = iovs; // mBufferSize may get changed by stream

  DBGMSG("\ntrying to start audio stream @ %i sr, %i buffer size\nindev = %i:%s\noutdev = %i:%s\ninputs = %i from channel %i\noutputs = %i from channel %i\n",
         sr,
         mBufferSize,
         inId,
         GetAudioDeviceName(inId).c_str(),
         outId,
         GetAudioDeviceName(outId).c_str(),
         iParams.nChannels,
         iParams.firstChannel + 1,
         oParams.nChannels,
         oParams.firstChannel + 1);

  RtAudio::StreamOptions options;
  options.flags = RTAUDIO_NONINTERLEAVED;
  // options.streamName = BUNDLE_NAME; // JACK stream name, not used on other streams

  mBufIndex = 0;
  mSamplesElapsed = 0;
  mSampleRate = (double) sr;
  mVecWait = 0;
  mAudioEnding = false;
  mAudioDone = false;

  mInputBufPtrs.Empty();
  mOutputBufPtrs.Empty();

  mIPlug->SetBlockSize(APP_SIGNAL_VECTOR_SIZE);
  mIPlug->SetSampleRate(mSampleRate);
  mIPlug->OnReset();

  try
  {
    mDAC->openStream(&oParams,
                     iParams.nChannels > 0 ? &iParams : nullptr,
                     RTAUDIO_FLOAT64,
                     sr,
                     &mBufferSize,
                     &AudioCallback,
                     this,
                     &options /*, &ErrorCallback */);

    for (int i = 0; i < iParams.nChannels; i++)
      mInputBufPtrs.Add(nullptr); // will be set in callback

    for (int i = 0; i < oParams.nChannels; i++)
      mOutputBufPtrs.Add(nullptr); // will be set in callback

    mDAC->startStream();
    mActiveState = mState;
  }
  catch (RtAudioError& e)
  {
    e.printMessage();
    return false;
  }

  return true;
}'''

host_cpp = replace_regex_once(
    host_cpp,
    r"bool IPlugAPPHost::InitAudio\(uint32_t inId, uint32_t outId, uint32_t sr, uint32_t iovs\)\s*\{.*?\n\}\s*\n\s*bool IPlugAPPHost::InitMidi\(\)",
    new_init_audio + "\n\nbool IPlugAPPHost::InitMidi()",
    "InitAudio",
)
write(host_cpp_path, host_cpp)


dialog_path = "IPlug/APP/IPlugAPP_dialog.cpp"
dialog = read(dialog_path)

new_input_list = r'''void IPlugAPPHost::PopulateAudioInputList(HWND hwndDlg, RtAudio::DeviceInfo* info)
{
  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_L, CB_RESETCONTENT, 0, 0);
  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_R, CB_RESETCONTENT, 0, 0);

  if (!info->probed)
    return;

  const int requiredChannels = GetPlug()->MaxNChannels(ERoute::kInput);
  const int availableChannels = static_cast<int>(info->inputChannels);
  const int startCount = requiredChannels > 0 ? availableChannels - requiredChannels + 1 : 0;

  if (startCount <= 0)
    return;

  if (mState.mAudioInChanL < 1 || mState.mAudioInChanL > static_cast<uint32_t>(startCount))
    mState.mAudioInChanL = 1;

  mState.mAudioInChanR = mState.mAudioInChanL + static_cast<uint32_t>(requiredChannels - 1);

  WDL_String buf;
  for (int i = 0; i < startCount; i++)
  {
    buf.SetFormatted(20, "%i", i + 1);
    SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_L, CB_ADDSTRING, 0, (LPARAM) buf.Get());
  }

  for (int i = 0; i < availableChannels; i++)
  {
    buf.SetFormatted(20, "%i", i + 1);
    SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_R, CB_ADDSTRING, 0, (LPARAM) buf.Get());
  }

  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_L, CB_SETCURSEL, mState.mAudioInChanL - 1, 0);
  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_R, CB_SETCURSEL, mState.mAudioInChanR - 1, 0);
  EnableWindow(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_IN_R), FALSE);
}'''

dialog = replace_regex_once(
    dialog,
    r"void IPlugAPPHost::PopulateAudioInputList\(HWND hwndDlg, RtAudio::DeviceInfo\* info\)\s*\{.*?\n\}\s*\n\s*void IPlugAPPHost::PopulateAudioOutputList",
    new_input_list + "\n\nvoid IPlugAPPHost::PopulateAudioOutputList",
    "PopulateAudioInputList",
)

new_output_list = r'''void IPlugAPPHost::PopulateAudioOutputList(HWND hwndDlg, RtAudio::DeviceInfo* info)
{
  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_L, CB_RESETCONTENT, 0, 0);
  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_R, CB_RESETCONTENT, 0, 0);

  if (!info->probed)
    return;

  const int requiredChannels = GetPlug()->MaxNChannels(ERoute::kOutput);
  const int availableChannels = static_cast<int>(info->outputChannels);
  const int startCount = requiredChannels > 0 ? availableChannels - requiredChannels + 1 : 0;

  if (startCount <= 0)
    return;

  if (mState.mAudioOutChanL < 1 || mState.mAudioOutChanL > static_cast<uint32_t>(startCount))
    mState.mAudioOutChanL = 1;

  mState.mAudioOutChanR = mState.mAudioOutChanL + static_cast<uint32_t>(requiredChannels - 1);

  WDL_String buf;
  for (int i = 0; i < startCount; i++)
  {
    buf.SetFormatted(20, "%i", i + 1);
    SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_L, CB_ADDSTRING, 0, (LPARAM) buf.Get());
  }

  for (int i = 0; i < availableChannels; i++)
  {
    buf.SetFormatted(20, "%i", i + 1);
    SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_R, CB_ADDSTRING, 0, (LPARAM) buf.Get());
  }

  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_L, CB_SETCURSEL, mState.mAudioOutChanL - 1, 0);
  SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_R, CB_SETCURSEL, mState.mAudioOutChanR - 1, 0);
  EnableWindow(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_OUT_R), FALSE);
}'''

dialog = replace_regex_once(
    dialog,
    r"void IPlugAPPHost::PopulateAudioOutputList\(HWND hwndDlg, RtAudio::DeviceInfo\* info\)\s*\{.*?\n\}\s*\n\s*// This has to get called",
    new_output_list + "\n\n// This has to get called",
    "PopulateAudioOutputList",
)

dialog = replace_once(
    dialog,
    """              // Reset IO
              mState.mAudioOutChanL = 1;
              mState.mAudioOutChanR = 2;""",
    """              // Reset IO
              mState.mAudioInChanL = 1;
              mState.mAudioInChanR = 1;
              mState.mAudioOutChanL = 1;
              mState.mAudioOutChanR = 2;""",
    "driver-change channel reset",
)

new_in_l_case = r'''        case IDC_COMBO_AUDIO_IN_L:
          if (HIWORD(wParam) == CBN_SELCHANGE)
          {
            mState.mAudioInChanL = (int) SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_L, CB_GETCURSEL, 0, 0) + 1;
            const int requiredChannels = _this->GetPlug()->MaxNChannels(ERoute::kInput);
            mState.mAudioInChanR = mState.mAudioInChanL + (requiredChannels > 0 ? requiredChannels - 1 : 0);
            SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_IN_R, CB_SETCURSEL, mState.mAudioInChanR - 1, 0);
          }
          break;'''

dialog = replace_regex_once(
    dialog,
    r"        case IDC_COMBO_AUDIO_IN_L:.*?          break;\s*\n\s*        case IDC_COMBO_AUDIO_IN_R:",
    new_in_l_case + "\n\n        case IDC_COMBO_AUDIO_IN_R:",
    "input-left selector",
)

dialog = replace_regex_once(
    dialog,
    r"        case IDC_COMBO_AUDIO_IN_R:.*?          break;\s*\n\s*        case IDC_COMBO_AUDIO_OUT_L:",
    """        case IDC_COMBO_AUDIO_IN_R:
          // RtAudio opens contiguous channel ranges; the right channel is derived from the selected first channel.
          break;

        case IDC_COMBO_AUDIO_OUT_L:""",
    "input-right selector",
)

new_out_l_case = r'''        case IDC_COMBO_AUDIO_OUT_L:
          if (HIWORD(wParam) == CBN_SELCHANGE)
          {
            mState.mAudioOutChanL = (int) SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_L, CB_GETCURSEL, 0, 0) + 1;
            const int requiredChannels = _this->GetPlug()->MaxNChannels(ERoute::kOutput);
            mState.mAudioOutChanR = mState.mAudioOutChanL + (requiredChannels > 0 ? requiredChannels - 1 : 0);
            SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_OUT_R, CB_SETCURSEL, mState.mAudioOutChanR - 1, 0);
          }
          break;'''

dialog = replace_regex_once(
    dialog,
    r"        case IDC_COMBO_AUDIO_OUT_L:.*?          break;\s*\n\s*        case IDC_COMBO_AUDIO_OUT_R:",
    new_out_l_case + "\n\n        case IDC_COMBO_AUDIO_OUT_R:",
    "output-left selector",
)

dialog = replace_regex_once(
    dialog,
    r"        case IDC_COMBO_AUDIO_OUT_R:.*?          break;\s*\n\s*//        case IDC_CB_MONO_INPUT:",
    """        case IDC_COMBO_AUDIO_OUT_R:
          // RtAudio opens contiguous channel ranges; the right channel is derived from the selected first channel.
          break;

//        case IDC_CB_MONO_INPUT:""",
    "output-right selector",
)

write(dialog_path, dialog)
