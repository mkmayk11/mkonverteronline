const fileInput = document.getElementById("fileInput");
const formatSelect = document.getElementById("formatSelect");
const icoOptions = document.getElementById("icoOptions");
const icoSize = document.getElementById("icoSize");
const convertBtn = document.getElementById("convertBtn");
const status = document.getElementById("status");

// Mostrar opções de ICO se selecionado
formatSelect.addEventListener("change", () => {
    if (formatSelect.value === "ico") {
        icoOptions.style.display = "block";
    } else {
        icoOptions.style.display = "none";
    }
});

// Converter arquivo
convertBtn.addEventListener("click", () => {
    const file = fileInput.files[0];
    const outputFormat = formatSelect.value;
    const outputName = document.getElementById("outputName").value || "";

    if (!file) {
        alert("Selecione um arquivo!");
        return;
    }
    if (!outputFormat) {
        alert("Selecione um formato de saída!");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("format", outputFormat);
    formData.append("name", outputName);
    if (outputFormat === "ico") formData.append("icoSize", icoSize.value);

    status.textContent = "Convertendo...";

    fetch("/convert", {
        method: "POST",
        body: formData
    })
    .then(res => res.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = outputName ? `${outputName}.${outputFormat}` : `convertido.${outputFormat}`;
        a.click();
        URL.revokeObjectURL(url);
        status.textContent = "Conversão concluída!";
    })
    .catch(err => {
        console.error(err);
        status.textContent = "Erro na conversão!";
    });
});
