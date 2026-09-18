# Kordoc Parser

HWP/HWPX 문서를 Markdown 파일로 변환하는 데스크톱 앱이다.

## 알려진 한계

- Markdown 표 문법은 셀 병합(`rowspan`, `colspan`)을 지원하지 않는다.
- 따라서 원본 표에 병합된 셀이 있으면 병합 구조를 보존하기 위해 해당 표는 Markdown 파일 안에 HTML `<table>` 형식으로 출력된다.
- 병합 표를 순수 Markdown 표로 바꾸려면 병합을 해제하고 셀 값을 반복하거나 빈칸으로 처리해야 하므로 원본 구조가 손실될 수 있다.
