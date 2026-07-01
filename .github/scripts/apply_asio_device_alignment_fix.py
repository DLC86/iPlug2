from pathlib import Path
import re

path = Path("IPlug/APP/IPlugAPP_dialog.cpp")
text = path.read_text(encoding="utf-8")

pattern = re.compile(
    r"void IPlugAPPHost::PopulateDriverSpecificControls\(HWND hwndDlg\)\n\{.*?\n\}\n\nvoid IPlugAPPHost::PopulateAudioDialogs",
    re.S,
)

replacement = r'''void IPlugAPPHost::PopulateDriverSpecificControls(HWND hwndDlg)
{
#ifdef OS_WIN
  const int driverType = (int) SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_DRIVER, CB_GETCURSEL, 0, 0);
  const bool isASIO = driverType == kDeviceASIO;

  ComboBox_Enable(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_IN_DEV), !isASIO);
  Button_Enable(GetDlgItem(hwndDlg, IDC_BUTTON_OS_DEV_SETTINGS), isASIO);
#else
  const bool isASIO = false;
#endif

  int indevidx = 0;
  int outdevidx = 0;

  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_RESETCONTENT,0,0);
  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_RESETCONTENT,0,0);

  // ASIO uses one driver for both directions. Populate both selectors from
  // the same RtAudio device-id list so equal combo indices cannot refer to
  // different drivers when the filtered input/output lists differ.
  const std::vector<uint32_t>& inputDeviceList = isASIO ? mAudioOutputDevs : mAudioInputDevs;

  for (int i = 0; i < static_cast<int>(inputDeviceList.size()); i++)
  {
    const std::string deviceName = GetAudioDeviceName(inputDeviceList[i]);
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_ADDSTRING,0,(LPARAM)deviceName.c_str());

    const char* selectedName = isASIO ? mState.mAudioOutDev.Get() : mState.mAudioInDev.Get();
    if(!strcmp(deviceName.c_str(), selectedName))
      indevidx = i;
  }

  for (int i = 0; i < static_cast<int>(mAudioOutputDevs.size()); i++)
  {
    const std::string deviceName = GetAudioDeviceName(mAudioOutputDevs[i]);
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_ADDSTRING,0,(LPARAM)deviceName.c_str());

    if(!strcmp(deviceName.c_str(), mState.mAudioOutDev.Get()))
      outdevidx = i;
  }

  if (isASIO)
  {
    indevidx = outdevidx;

    if (!mAudioOutputDevs.empty())
    {
      const std::string deviceName = GetAudioDeviceName(mAudioOutputDevs[outdevidx]);
      mState.mAudioInDev.Set(deviceName.c_str());
      mState.mAudioOutDev.Set(deviceName.c_str());
    }
  }

  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_SETCURSEL, indevidx, 0);
  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_SETCURSEL, outdevidx, 0);

  RtAudio::DeviceInfo inputDevInfo;
  RtAudio::DeviceInfo outputDevInfo;

  if (isASIO && !mAudioOutputDevs.empty())
  {
    // Use the exact selected ASIO driver for both channel lists and sample rates.
    outputDevInfo = mDAC->getDeviceInfo(mAudioOutputDevs[outdevidx]);
    inputDevInfo = outputDevInfo;
    PopulateAudioInputList(hwndDlg, &inputDevInfo);
    PopulateAudioOutputList(hwndDlg, &outputDevInfo);
  }
  else
  {
    if (!mAudioInputDevs.empty())
    {
      inputDevInfo = mDAC->getDeviceInfo(mAudioInputDevs[indevidx]);
      PopulateAudioInputList(hwndDlg, &inputDevInfo);
    }

    if (!mAudioOutputDevs.empty())
    {
      outputDevInfo = mDAC->getDeviceInfo(mAudioOutputDevs[outdevidx]);
      PopulateAudioOutputList(hwndDlg, &outputDevInfo);
    }
  }

  PopulateSampleRateList(hwndDlg, &inputDevInfo, &outputDevInfo);
}

void IPlugAPPHost::PopulateAudioDialogs'''

updated, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(f"Expected one PopulateDriverSpecificControls block, found {count}")

path.write_text(updated, encoding="utf-8")
