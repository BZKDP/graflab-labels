# Замена отсутствующих/битых шрифтов в основе Инозитол + сохранение fixed CDR/PDF
$ErrorActionPreference='Continue'
Add-Type @'
using System;using System.Runtime.InteropServices;using System.Text;
public class WN{
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb,IntPtr l);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint m,IntPtr w,IntPtr l);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out R r);
public delegate bool EnumProc(IntPtr h,IntPtr l);
public struct R{public int L,T,Rt,B;}
}
'@

# 1. Убить все залипшие Corel
Get-Process CorelDRW -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 5

# 2. Новый экземпляр + асинхронный ожидатель nag-окна: слать Enter каждые 5с первые 60с
$job = Start-Job -ScriptBlock {
  Add-Type @'
using System;using System.Runtime.InteropServices;using System.Text;
public class WJ{
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb,IntPtr l);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint m,IntPtr w,IntPtr l);
public delegate bool EnumProc(IntPtr h,IntPtr l);
}
'@
  for($k=0;$k -lt 12;$k++){
    Start-Sleep 5
    $pids=(Get-Process CorelDRW -ErrorAction SilentlyContinue).Id
    if(-not $pids){continue}
    [WJ]::EnumWindows({param($h,$l)
      $p=0;[WJ]::GetWindowThreadProcessId($h,[ref]$p)|Out-Null
      if(@($using:null) -eq $null){}
      $sb=New-Object System.Text.StringBuilder 256
      [WJ]::GetWindowText($h,$sb,256)|Out-Null
      $t=$sb.ToString()
      if($t -match 'Оценочная|Evaluation'){
        # Enter обычно нажимает дефолтную кнопку «Продолжить»
        [WJ]::PostMessage($h,0x0100,[IntPtr]0x0D,[IntPtr]::Zero)|Out-Null
        [WJ]::PostMessage($h,0x0101,[IntPtr]0x0D,[IntPtr]::Zero)|Out-Null
      }
      return $true},[IntPtr]::Zero)|Out-Null
  }
}

$app=New-Object -ComObject CorelDRAW.Application
$app.Visible=$true
Write-Output ('COM created')
$doc=$app.OpenDocument((Join-Path $PSScriptRoot 'input/1787737791687-744172468.cdr'))
Write-Output ('opened: '+$doc.Title)
Stop-Job $job -ErrorAction SilentlyContinue

# 3. Замена шрифтов
$map=@{
  'DIN Pro Cond'='PT Sans Narrow'
  'DIN Pro Cond Bold'='PT Sans Narrow'
  'DINPro-CondensedRegular'='PT Sans Narrow'
  'Miriam Libre'='PT Sans Narrow'
  'Yu Gothic UI'='PT Sans Narrow'
  'Averta CY Semibold'='Montserrat'
}
$boldish=@('DIN Pro Cond Bold','Miriam Libre','Yu Gothic UI','Averta CY Semibold')
$changed=0
foreach($s in $doc.ActivePage.Shapes.All()){
  if($s.Type -ne 6){continue}
  $story=$s.Text.Story
  $n=$story.Characters.Count
  $i=1
  while($i -le $n){
    $j=$i
    $f=$story.Range($i,$i+1).Font
    while($j -lt $n){
      if($story.Range($j+1,$j+2).Font -ne $f){break}
      $j++
    }
    if($map.ContainsKey($f)){
      $rr=$story.Range($i,$j+1)
      $rr.Font=$map[$f]
      if($boldish -contains $f){ try{$rr.Bold=$true}catch{} }
      $changed++
      Write-Output ('replaced ['+$f+'] chars '+$i+'-'+$j)
    }
    $i=$j+1
  }
}
Write-Output ('ranges changed: '+$changed)

# 4. Сохранить копию + PDF
$doc.SaveAs((Join-Path $PSScriptRoot 'inositol_base_fixed.cdr'))
$doc.PublishToPDF((Join-Path $PSScriptRoot 'inositol_base_fixed.pdf'))
Write-Output 'SAVED_AND_EXPORTED'
$doc.Close()
