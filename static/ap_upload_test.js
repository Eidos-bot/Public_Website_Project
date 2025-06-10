//Javascript inside an html doc inside a python environment. Remember your syntax rules.
// Realized the above isn't a good idea if you want to keep your code from being seen in the html.

document.addEventListener("DOMContentLoaded", function() {

    const fileInput = document.getElementById("file");
    const pdfPreview = document.getElementById("pdfPreview");
    const  gl_input = document.getElementById("GL");
    const submitButton = document.getElementById("submit_button")
    const fixedAsset = document.getElementById("asset_chk")
    const prj_id = document.getElementById("ProjectID")
    const nglGroup = document.getElementById("glGroup")
    const sidebarGroup = document.getElementById("sidebarContainer")
    const removeButtonElement = document.getElementById("removeGlClass")
    const prePaidButtonElement = document.getElementById("pre_paid")

    const glCodeArray = document.getElementsByName("GL")
    const prjIdArray = document.getElementsByName("Project ID")
    const amountArray = document.getElementsByName("Amount")
    const prePaidCheckArray = document.getElementsByName("Prepaid")
    const glGroupArray = document.getElementsByClassName("parent gl-parent")
    const glAmountTotalElement = document.getElementById("glAmountTotal")

    let glGroupCounter = 0
    let glGroupIdTracker = 0

    let newGl = document.getElementById("newGlButton")
    // Project ID will restrict
    let eventListenerCount = 0

    document.addEventListener("input",function(){arrayOfElements()})
    document.addEventListener("change",function(){arrayOfElements()})
    document.addEventListener("click",function(){arrayOfElements()})

    // So now i have a list of all glGroups, new and old, and if any of them evaluate as false, I get the submit button disabled.
    // It has to be said this is not easily maintained, to me, because it doesn't flow as nicely as I'm used to in python.
    // I'm not used to dynamic lists that change on runtime.
    function arrayOfElements(){
        // This is list comprehension basically. Looks like lambda.
        let totalGlAmount = 0
        const mapglCodeArray = Array.from(glCodeArray).map((el)=>el.value)
        const mapprjIdArray = Array.from(prjIdArray).map((el)=>el.value)
        const mapamountArray = Array.from(amountArray).map((el)=>totalGlAmount += isNaN(el.valueAsNumber) ? 0 : el.valueAsNumber)
        const mapprePaidCheckArray = Array.from(prePaidCheckArray).map((el)=>el.checked)
        if (isNaN(totalGlAmount)){
            glAmountTotalElement.value = 0
        }
        else{
            glAmountTotalElement.value=totalGlAmount
        }

        console.log(totalGlAmount)
        const mapglGroupArray = Array.from(glGroupArray).map((glGroupElement)=>{
            return {
            gl: glGroupElement.querySelectorAll('[name="GL"]'),
            prepaid: glGroupElement.querySelectorAll('[name="Prepaid"]'),
            project_id: glGroupElement.querySelectorAll('[name="Project ID"]')
            }
        })
        // console.log(mapglCodeArray)
        // console.log(mapprjIdArray)
        // console.log(mapamountArray)
        // console.log(mapprePaidCheckArray)
        // console.log(mapglGroupArray)
        let allValid = false
        mapglGroupArray.forEach(function(nl){
            if(fixedAsset.checked) {

                let prePaidFACheck = nl['prepaid'][0].checked
                let glFACheck = nl['gl'][0].value
                let projidFAChecker = nl['project_id'][0].value

                if (!(prePaidFACheck === true || (projidFAChecker !== "" && glFACheck.startsWith("4")))) {
                    allValid = true
                    console.log("Asset check evaluates to false")
                }

            }

        })
        submitButton.disabled = allValid

    }


    //So weird compare to python functions. if there's no input you care to have, then just the name of the function
    //is fine. But if there is, then you need to use function like you would when there's no set function, and
    //then use the function with the parameter.
    newGl.addEventListener("click", function(){newGlCreation(nglGroup)});




    function delGlGroup(currentGlId){
        if(glGroupCounter>0){
           // let maxGlGroup = document.getElementById(`${currentGlId}${glGroupCounter}`)
            let delGlGroupTarget = document.getElementById(`${currentGlId}`)
           glGroupCounter-=1
           delGlGroupTarget.remove()
            console.log(glGroupCounter)
            if(newGl.disabled===true){
                newGl.disabled=false

            }

        }

    }

    //Use the variable this when referring to the value attached to a listener.

    prePaidButtonElement.addEventListener("change",function(){prePaidSet(this)})

    // This is so I can disable the gl when the prepaid thing is checked.
    // Note to self: use readonly instead of disabled if you still want the values.
    function prePaidSet(listenTarget){
        let chosenId = listenTarget.id
        let isoId = chosenId.replace("pre_paid","")
        if(listenTarget.checked){
            if(isoId === ""){
                const orgGlCodeInputElementd = document.getElementById("GL")
                orgGlCodeInputElementd.value = "1404051000"
                orgGlCodeInputElementd.readOnly = true
                orgGlCodeInputElementd.style.color = "red"
                //console.log(orgGlCodeInputElementd)
            }
            else {
                const nonorgGlCodeInputElementd = document.getElementById("GL"+isoId)
                nonorgGlCodeInputElementd.value = "1404051000"
                nonorgGlCodeInputElementd.readOnly = true
                nonorgGlCodeInputElementd.style.color = "red"
                //console.log(nonorgGlCodeInputElementd)
            }

        }
        else {
            if(isoId === ""){
                const orgGlCodeInputElementd = document.getElementById("GL")
                orgGlCodeInputElementd.value = ""
                orgGlCodeInputElementd.readOnly = false
                orgGlCodeInputElementd.style.color = "black"
                //console.log(orgGlCodeInputElementd)
            }
            else {
                const nonorgGlCodeInputElementd = document.getElementById("GL"+isoId)
                nonorgGlCodeInputElementd.value = ""
                nonorgGlCodeInputElementd.readOnly = false
                nonorgGlCodeInputElementd.style.color = "black"
                //console.log(nonorgGlCodeInputElementd)
            }

        }
    }

    function newGlCreation(targetEl){
        glGroupCounter +=1;
        glGroupIdTracker +=1;
        console.log(glGroupCounter)
        let new_gl_group = targetEl.cloneNode(true);
        let newGlId = new_gl_group.getAttribute("id");
        let projidclass = document.getElementById("projIdClassId")
        // let projclassidid = projidclass.document.getAttribute("id")
        // querySelectorAll gives all attributes that matches your query. An actual list.
        let idContainer = new_gl_group.querySelectorAll("[id]");


        for (let el of idContainer){

            el.setAttribute("id",`${el.id}${glGroupIdTracker}`)

        }

        new_gl_group.setAttribute("id",`${newGlId}${glGroupIdTracker}`);


        // // newGl.remove();
        // new_gl_group.classList.add("sidebar");

        sidebarGroup.appendChild(new_gl_group);
        let newProjId = projidclass.id+glGroupIdTracker
        let newRemoveButtonId = `${removeButtonElement.id}${glGroupIdTracker}`
        let newRemoveButtonElement = document.getElementById(newRemoveButtonId);
        let newProjIdElement = document.getElementById(newProjId);
        console.log("The new remove id seen is:" + newRemoveButtonId)
        newProjIdElement.style.display='flex';
        newProjIdElement.style.flexDirection='row';
        newRemoveButtonElement.style.marginTop='auto';


        newRemoveButtonElement.addEventListener('click',function(){delGlGroup(new_gl_group.id)})

        if (glGroupCounter>=11){
            newGl.disabled=true;
        }
        let newPrepaidCheck = document.getElementById(`${prePaidButtonElement.id}${glGroupIdTracker}`)
        //console.log(`${prePaidButtonElement.id}${glGroupCounter}`)
        //console.log(newPrepaidCheck)
        newPrepaidCheck.addEventListener("change",function(){prePaidSet(this)})
        clearChildren(new_gl_group)
        // let newGlButton = document.getElementById("newGlButton");
        //
        // newGlButton.addEventListener("click", function(){newGlCreation(new_gl_group)});

    }
    //
    function clearChildren(elementNode){
        let childNodeIds = elementNode.querySelectorAll("[id]")

        childNodeIds.forEach(function(nodeId) {
            //console.log(nodeId)

            if(nodeId.type==="text"){
                nodeId.value=''
                nodeId.readOnly=false
                nodeId.style.color = "black"
            }
            else if(nodeId.type==="checkbox"){
                nodeId.checked = false
            }
            else if(nodeId.type==="number"){
                nodeId.value = ''
            }


        });
    }

    //This is neater than load event
    fileInput.addEventListener("change", function(event) {
        pdfPreview.innerHTML = '';

        const file = event.target.files[0];
        if (file) {
            const url = URL.createObjectURL(file);

            const iframe = document.createElement("iframe");
            iframe.src = url;
            iframe.width = "100%";
            iframe.height = "600px";
            iframe.style.border = "1px solid #ccc";

            pdfPreview.appendChild(iframe);

            iframe.onload = function() {
                URL.revokeObjectURL(iframe.src);
            };
        }
  });
});