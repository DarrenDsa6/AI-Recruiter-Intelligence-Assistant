import html2canvas from "html2canvas-pro";
import jsPDF from "jspdf";

export async function generateReportPdf(elementId, filename = "AI-Recruiter-Report.pdf") {
  const element = document.getElementById(elementId);
  if (!element) return;

  const canvas = await html2canvas(element, {
    scale: 2,
    useCORS: true,
    backgroundColor: "#0B0F19",
    logging: false,
  });

  const imgData = canvas.toDataURL("image/png");
  const imgWidth = 210;
  const imgHeight = (canvas.height * imgWidth) / canvas.width;

  const pdf = new jsPDF("p", "mm", "a4");
  let heightLeft = imgHeight;
  let position = 0;

  pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
  heightLeft -= pdf.internal.pageSize.getHeight();

  while (heightLeft > 0) {
    position = heightLeft - imgHeight;
    pdf.addPage();
    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
    heightLeft -= pdf.internal.pageSize.getHeight();
  }

  pdf.save(filename);
}
