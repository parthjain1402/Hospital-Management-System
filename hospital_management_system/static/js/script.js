function toggleSecretKey() { 
 
    let role = document.getElementById('role').value; 
    let field = document.getElementById('secretKeyField'); 
 
    if (role === 'Patient') { 
        field.style.display = 'none'; 
    } else { 
        field.style.display = 'block'; 
    } 
} 