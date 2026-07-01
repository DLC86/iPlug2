from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} block in {path}, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


path = "IPlug/APP/IPlugAPP_dialog.cpp"

replace_once(
    path,
    '''  for (int i=0; i<nOutputStartOptions; i++)
  {
    buf.SetFormatted(20, "%i", i+1);
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_L,CB_ADDSTRING,0,(LPARAM)buf.Get());
  }''',
    '''  for (int i=0; i<nOutputStartOptions; i++)
  {
    if (nOutputChans > 1)
      buf.SetFormatted(20, "%i-%i", i + 1, i + nOutputChans);
    else
      buf.SetFormatted(20, "%i", i + 1);

    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_L,CB_ADDSTRING,0,(LPARAM)buf.Get());
  }''',
    "output route labels",
)

old_function = '''void IPlugAPPHost::PopulateDriverSpecificControls(HWND hwndDlg)
{
#ifdef OS_WIN
  int driverType = (int) SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_DRIVER, CB_GETCURSEL, 0, 0);
  if(driverType == kDeviceASIO)
  {
    ComboBox_Enable(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_IN_DEV), FALSE);
    Button_Enable(GetDlgItem(hwndDlg, IDC_BUTTON_OS_DEV_SETTINGS), TRUE);
  }
  else
  {
    ComboBox_Enable(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_IN_DEV), TRUE);
    Button_Enable(GetDlgItem(hwndDlg, IDC_BUTTON_OS_DEV_SETTINGS), FALSE);
  }
#endif

  int indevidx = 0;
  int outdevidx = 0;

  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_RESETCONTENT,0,0);
  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_RESETCONTENT,0,0);

  for (int i = 0; i<mAudioInputDevs.size(); i++)
  {
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_ADDSTRING,0,(LPARAM)GetAudioDeviceName(mAudioInputDevs[i]).c_str());

    if(!strcmp(GetAudioDeviceName(mAudioInputDevs[i]).c_str(), mState.mAudioInDev.Get()))
      indevidx = i;
  }

  for (int i = 0; i<mAudioOutputDevs.size(); i++)
  {
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_ADDSTRING,0,(LPARAM)GetAudioDeviceName(mAudioOutputDevs[i]).c_str());

    if(!strcmp(GetAudioDeviceName(mAudioOutputDevs[i]).c_str(), mState.mAudioOutDev.Get()))
      outdevidx = i;
  }

#ifdef OS_WIN
  if(driverType == kDeviceASIO)
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_SETCURSEL, outdevidx, 0);
  else
#endif
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_SETCURSEL, indevidx, 0);

  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_SETCURSEL, outdevidx, 0);

  RtAudio::DeviceInfo inputDevInfo;
  RtAudio::DeviceInfo outputDevInfo;

  if (mAudioInputDevs.size())
  {
    inputDevInfo = mDAC->getDeviceInfo(mAudioInputDevs[indevidx]);
    PopulateAudioInputList(hwndDlg, &inputDevInfo);
  }

  if (mAudioOutputDevs.size())
  {
    outputDevInfo = mDAC->getDeviceInfo(mAudioOutputDevs[outdevidx]);
    PopulateAudioOutputList(hwndDlg, &outputDevInfo);
  }

  PopulateSampleRateList(hwndDlg, &inputDevInfo, &outputDevInfo);
}'''

new_function = '''void IPlugAPPHost::PopulateDriverSpecificControls(HWND hwndDlg)
{
#ifdef OS_WIN
  const int driverType = (int) SendDlgItemMessage(hwndDlg, IDC_COMBO_AUDIO_DRIVER, CB_GETCURSEL, 0, 0);
  const bool isASIO = driverType == kDeviceASIO;

  ComboBox_Enable(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_IN_DEV), !isASIO);
  Button_Enable(GetDlgItem(hwndDlg, IDC_BUTTON_OS_DEV_SETTINGS), isASIO);
#else
  const bool isASIO = false;
#endif

  std::vector<uint32_t> asioDuplexDevs;
  const std::vector<uint32_t>* inputDevs = &mAudioInputDevs;
  const std::vector<uint32_t>* outputDevs = &mAudioOutputDevs;

#ifdef OS_WIN
  if (isASIO)
  {
    // ASIO uses one driver for both directions. Build a single duplex list so
    // the disabled input selector, output selector, and channel information
    // all refer to the same RtAudio device ID.
    for (const uint32_t deviceId : mAudioOutputDevs)
    {
      if (std::find(mAudioInputDevs.begin(), mAudioInputDevs.end(), deviceId) != mAudioInputDevs.end())
        asioDuplexDevs.push_back(deviceId);
    }

    inputDevs = &asioDuplexDevs;
    outputDevs = &asioDuplexDevs;
  }
#endif

  int indevidx = 0;
  int outdevidx = 0;

  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_RESETCONTENT,0,0);
  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_RESETCONTENT,0,0);

  for (int i = 0; i < static_cast<int>(inputDevs->size()); i++)
  {
    const char* deviceName = GetAudioDeviceName((*inputDevs)[i]).c_str();
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_ADDSTRING,0,(LPARAM)deviceName);

    const char* selectedName = isASIO ? mState.mAudioOutDev.Get() : mState.mAudioInDev.Get();
    if(!strcmp(deviceName, selectedName))
      indevidx = i;
  }

  for (int i = 0; i < static_cast<int>(outputDevs->size()); i++)
  {
    const char* deviceName = GetAudioDeviceName((*outputDevs)[i]).c_str();
    SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_ADDSTRING,0,(LPARAM)deviceName);

    if(!strcmp(deviceName, mState.mAudioOutDev.Get()))
      outdevidx = i;
  }

  if (isASIO)
  {
    // The output selection is authoritative for ASIO. Keep the stored input
    // device synchronized and use the exact same device index for both menus.
    indevidx = outdevidx;
    if (!outputDevs->empty())
    {
      const char* selectedName = GetAudioDeviceName((*outputDevs)[outdevidx]).c_str();
      mState.mAudioInDev.Set(selectedName);
      mState.mAudioOutDev.Set(selectedName);
    }
  }

  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_IN_DEV,CB_SETCURSEL, indevidx, 0);
  SendDlgItemMessage(hwndDlg,IDC_COMBO_AUDIO_OUT_DEV,CB_SETCURSEL, outdevidx, 0);

  RtAudio::DeviceInfo inputDevInfo;
  RtAudio::DeviceInfo outputDevInfo;

  if (isASIO && !outputDevs->empty())
  {
    // Query the selected ASIO driver once and use that same DeviceInfo for
    // input channels, output channels, and sample rates.
    outputDevInfo = mDAC->getDeviceInfo((*outputDevs)[outdevidx]);
    inputDevInfo = outputDevInfo;
    PopulateAudioInputList(hwndDlg, &inputDevInfo);
    PopulateAudioOutputList(hwndDlg, &outputDevInfo);
  }
  else
  {
    if (!inputDevs->empty())
    {
      inputDevInfo = mDAC->getDeviceInfo((*inputDevs)[indevidx]);
      PopulateAudioInputList(hwndDlg, &inputDevInfo);
    }

    if (!outputDevs->empty())
    {
      outputDevInfo = mDAC->getDeviceInfo((*outputDevs)[outdevidx]);
      PopulateAudioOutputList(hwndDlg, &outputDevInfo);
    }
  }

  PopulateSampleRateList(hwndDlg, &inputDevInfo, &outputDevInfo);
}'''

replace_once(path, old_function, new_function, "PopulateDriverSpecificControls")

replace_once(
    path,
    '''            getComboString(mState.mAudioOutDev, IDC_COMBO_AUDIO_OUT_DEV, idx);

            // Reset IO
            mState.mAudioOutChanL = 1;
            mState.mAudioOutChanR = 2;

            _this->PopulateDriverSpecificControls(hwndDlg);''',
    '''            getComboString(mState.mAudioOutDev, IDC_COMBO_AUDIO_OUT_DEV, idx);

#ifdef OS_WIN
            if (mState.mAudioDriverType == kDeviceASIO)
            {
              mState.mAudioInDev.Set(mState.mAudioOutDev.Get());
              mState.mAudioInChanL = 1;
              mState.mAudioInChanR = 1;
            }
#endif

            // Reset IO
            mState.mAudioOutChanL = 1;
            mState.mAudioOutChanR = 2;

            _this->PopulateDriverSpecificControls(hwndDlg);''',
    "ASIO output selection synchronization",
)
