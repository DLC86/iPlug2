from pathlib import Path


def change(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(path)
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


change(
    "IPlug/APP/IPlugAPP_host.cpp",
    '      mINIPath.Append("\\\\settings.ini");',
    '      mINIPath.Append("settings.ini");',
)

change(
    "IPlug/APP/IPlugAPP_host.cpp",
    "  mAudioEnding = false;\n  mAudioDone = false;\n  \n  mIPlug->SetBlockSize(APP_SIGNAL_VECTOR_SIZE);",
    "  mAudioEnding = false;\n  mAudioDone = false;\n\n  mInputBufPtrs.Empty();\n  mOutputBufPtrs.Empty();\n  \n  mIPlug->SetBlockSize(APP_SIGNAL_VECTOR_SIZE);",
)

change(
    "IPlug/APP/IPlugAPP_dialog.cpp",
    "  return availableChannels > streamChannels ? availableChannels - streamChannels + 1 : 1;",
    "  return availableChannels >= streamChannels ? availableChannels - streamChannels + 1 : 0;",
)

change(
    "IPlug/APP/IPlugAPP_dialog.cpp",
    "  EnableWindow(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_IN_R), nInputChans > 1);",
    "  EnableWindow(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_IN_R), FALSE);",
)

change(
    "IPlug/APP/IPlugAPP_dialog.cpp",
    "  EnableWindow(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_OUT_R), nOutputChans > 1);",
    "  EnableWindow(GetDlgItem(hwndDlg, IDC_COMBO_AUDIO_OUT_R), FALSE);",
)

change(
    "IPlug/APP/IPlugAPP_dialog.cpp",
    "              // Reset IO\n              mState.mAudioOutChanL = 1;\n              mState.mAudioOutChanR = 2;",
    "              // Reset IO\n              mState.mAudioInChanL = 1;\n              mState.mAudioInChanR = 1;\n              mState.mAudioOutChanL = 1;\n              mState.mAudioOutChanR = 2;",
)
