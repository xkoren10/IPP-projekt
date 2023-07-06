<?php

/*
IPP 2021/2022, časť 2 - test.php
Autor: Matej Koreň
*/

// Výpis nápovedy
function help()
{
    print("    
    --help              - vypíše nápovedu\n
    --directory=path    - cesta k zložke s testami (implicitne aktuálna zložka)\n
    --recursive         - rekurzívne prehľadávanie zložky s testami\n
    --parse-script=file - cesta k skriptu parse.php\n
    --int-script=file   - cesta k skriptu interpret.py\n
    --parse-only        - testy parseru\n
    --int-only          - testy interpretu\n
    --noclean           - pri behu test.php nebude mazať pomocné súbory\n
    --jexamxml=path     - cesta k zložke s JAR balíkom s nástrojom A7Soft JExamXML a súborom s konfiguráciou");

}

// Trieda pre HTML dokument
class HTMLDocument 
{
    private $html;          
    public $all;      
    private $passed_count;     
    private $failed_count;     

    // Vytvorenie základnej štruktúry
    public function __construct($arguments)
    {
        $this->all = 0;
        $this->passed_count = 0;
        $this->failed_count = 0;
        $this->html =   "<!DOCTYPE html>\n".
                        "<html>\n".
                        "<head>\n<meta charset=\"utf-8\">\n<title>test.php</title>\n</head>\n".
                        "<body><center>\n<h1>VUT FIT, 2022</h1>\n<h2>IPP - test.php</h2>\n<h3>Autor: Matej Koreň</h3>\n\n".
                        "<br><br>Zadané argumenty: $arguments<br>".
                        "<style>
                        .fail{color:red;}.pass{color:green;}
                        body {max-width: max-content;
                            margin: auto; font-family: \"Segoe UI\", Arial, \"Noto Sans\", sans-serif; background: whitesmoke;}</style>\n\n";
    }

    // Koncové štatistiky, výpis na STDOUT
    public function RenderHTML()
    {
        $result = round($this->passed_count / $this->all * 100,2);

        $this->html = $this->html . "<br><br><div style=\"border: 3px;border-style:solid; border-color:green; padding: 1em; margin:10px; background: white\"><h2>Celkové výsledky:</h2>\n". 
                                    "<h3>Počet testov: $this->all</h3>\n".
                                    "<h3>Úspešných: $this->passed_count</h3>\n". 
                                    "<h3>Neúspešných: $this->failed_count</h3>\n".
                                    "<h2>Percentuálna úspešnosť: $result% </h2>\n". 
                                    "</div></center></body>\n</html>\n";
        echo $this->html;
    }

    // Začiatok adresára
    public function start_dir($dir)
    {
        $this->html = $this->html . "<br><br><h3>TESTOVANÁ ZLOŽKA:</h3>\n".
                                    "<details><summary><b>$dir</b></summary>\n";
    }

    // Štatistiky adresára
    public function end_dir_stats($passed, $failed)
    {
        $all = $passed + $failed;
        $result = round($passed / $all * 100,2);
        $this->html = $this->html . "</details><h3>Výsledky testovanej zložky</h3>\n".
                                    "<h4>Všetky testy: $all</h4>\n". 
                                    "<h4>Úspešné: $passed</h4>\n". 
                                    "<h4>Neúspešné: $failed</h4>\n".
                                    "<h3>Celkovo: $result%</h3>\n\n";
    }

    // Úspešný test
    public function test_passed($file)
    {
        $this->passed_count++;
        $this->html = $this->html . "<p>$this->all.: $file <span class=\"pass\">OK </span> <br></p>\n";
    }

    // Neúspešný test
    public function test_failed($file, $rc, $exp_rc)
    {
        $this->failed_count++;
        $this->html = $this->html . "<p>$this->all.: $file <span class=\"fail\">FAIL </span>".
        "--- Očakávaný návratový kód: $exp_rc / Vrátený kód: $rc<br></p>\n";
    }
}

// Trieda pre argumenty
class Arguments 
{    
    public $directory;
    public $recursive;
    public $parse_script;
    public $int_script;
    public $parse_only;
    public $int_only;
    public $jexamxml;
    public $noclean;

}


$args = new Arguments();         

parse_args($argc, $argv);  
check_arguments();             

// Pre lepšiu prehľadnosť vypíše v  HMTL zadané parametre
$arguments = implode(" ", $argv);
$html = new HTMLDocument($arguments);             

get_test_files($args->directory);           


// Ukončenie HTML a celého skriptu
$html->RenderHTML();                    

// Prehľadávanie zadanej zložky
function get_test_files($directory)
{
    global $args;

    $files = scandir($directory); // Vráti zoznam súborv v adresári

    if(isset($args->recursive)) // Ak je zadané rekurzívne vyhľadávanie
    {
        foreach($files as $file)
        {   
            if($file == "." || $file == "..")   // Preskočenie špecifickych ciet (proti nekonečnej rekurzii)
            { 
                continue;
            }
            if(is_dir($directory . "/" . $file))
            {
                get_test_files($directory . "/" . "$file"); // Rekurzívne volanie
            }
        }
    }

    // Spustenie testov v zložke
    start_test($directory); 
}


function start_test($dir)
{
    // Štatistiky
    $passed_count = 0;
    $failed_count = 0;

    $files = glob($dir . "/*.src"); // Pole .src súborov

    if($files == false) // Neexistujú .src súbory
    {   
        return;
    }

    foreach($files as $file)
    {
        check_files($file); // Kontrola .rc, .in a .out súborov
    }

    
    global $html, $args, $retval; 

    $html->start_dir($dir); // Výpis testovanej zložky

    foreach($files as $file) // Prechod poľom .src súborov
    {
        $html->all++; 
        
        $tmp = fopen(str_replace(".src", ".rc", $file), "r");  // Uloženie návratového kódu
        $rc = (int)fgets($tmp);
        fclose($tmp);

        $out_file = str_replace(".src", ".out", $file);     // Uloženie .out súboru
        $in_file = str_replace(".src", ".in", $file);       // Uloženie .in súboru


        //  Testovnie parse.php
        if($args->parse_only || (!$args->parse_only && !$args->int_only)) // Iba parser alebo oba skripty
        { 
            exec("php8.1 -f \"$args->parse_script\" < \"$file\" 2> /dev/null > tmp_parse.out ", result_code:$retval); // Spúšťací príkaz            
            
            if(($retval !== $rc)&&!(!$args->parse_only && !$args->int_only)) // Nezhodujú sa návratové kódy (len pri test parse.php)
            {
                $failed_count++;
                $html->test_failed(str_replace($dir, "", $file), $retval, $rc); // Test neprešiel
                if($args->noclean == false){
                    delete_files(); // Vymazanie pomocných súborov
                } 
                continue;
            }
            elseif(($retval !== 0)&&!(!$args->parse_only && !$args->int_only)) // Návratový kód je iný od nuly (len pri teste parse.php)
            { 
                if($args->parse_only)
                {  
                    $passed_count++;
                    $html->test_passed(str_replace($dir, "", $file)); // Test prešiel
                }
            }
            elseif (!(!$args->parse_only && !$args->int_only)) // Netestujeme oba skripty
            { 
                if (!(!$args->parse_only && !$args->int_only)){

                $jar_options = str_replace($args->jexamxml,"jexamxml.jar" , "options"); // Nastavenie JExamXML options súboru

                    if(!file_exists($jar_options))  // Ak options neexistujú, spustí sa bez nich
                    {
                        exec("java -jar \"$args->jexamxml\" \"$out_file\" \"tmp_parse.out\" ", $out, result_code: $retval);
                    }

                    else
                    {
                        exec("java -jar \"$args->jexamxml\" \"$jar_options\" \"$out_file\" \"tmp_parse.out\" ", $out, result_code: $retval); // Porovnanie s A7Soft JExamXML (len pri parse-only)
                    }
                }
                if(($retval !== 0)&&($retval !== 1)&&($retval !== 2)) // Nezhoda
                { 
                    $failed_count++;
                    $html->test_failed(str_replace($dir, "", $file), $retval, $rc); // Test Neprešiel
                    if($args->noclean == false && !(!$args->parse_only && !$args->int_only)){ 
                        delete_files(); // Vamazanie pomocnych suborov
                    } 
                    continue;
                }
                else
                {   
                    if($args->parse_only)
                    {
                        $passed_count++;
                        $html->test_passed(str_replace($dir, "", $file)); // Inak test prešiel
                    }                    
                }
            }
        }


        // Testovanie interpret.py
        if($args->int_only || (!$args->int_only && !$args->parse_only)) // Iba interpret alebo oba
        {  

            // Nastavenie vstupu podľa druhu testovania
            if($args->int_only)
            {  
                $src_file = $file;
            }
            else
            {   
                $src_file = "./tmp_parse.out";
            }

            exec("python3.8 \"$args->int_script\" --source=$src_file --input=$in_file 1> \"tmp_interpret.out\" 2> /dev/null", $out, $retval); // Spúšťací príkaz 

            
            if($retval !== $rc) // Nezhoda návratových kódov
            {  
                $failed_count++;
                $html->test_failed(str_replace($dir, "", $file), $retval, $rc); // Test neprešiel
            }
            else
            { 
                if($retval !== 0)
                {  
                    $passed_count++;
                    $html->test_passed(str_replace($dir, "", $file)); // Test prešiel
                }
                else
                {  
                    exec("diff tmp_interpret.out $out_file > /dev/null 2>&1", $outp, $retval); // Test výstupu pomocou diff()

                    if($retval !== 0) // Nezhoda
                    { 
                        $failed_count++;
                        $html->test_failed(str_replace($dir, "", $file), $retval, $rc); // Test neprešiel
                    }
                    else
                    {  
                        $passed_count++;
                        $html->test_passed(str_replace($dir, "", $file)); // Test prešiel
                    }
                }
            }
        }
    }    


    if($args->noclean == false){
        delete_files(); // Vymazaniee pomocných súborov
    } 


    $html->end_dir_stats($passed_count, $failed_count); // Po ukončení všetkých testov v zložke výpis štatistík zložky
}

// Funkcia na odstránenie pomocných súborov (--noclean sa kontroluje pred jej volaním)
function delete_files()
{
    exec("rm -f tmp_parse.out");
    exec("rm -f tmp_interpret.out");
}


// Kontrola výskytu suborov (pripadne ich vytvorenie)
function check_files($file)
{
    // Subor .in
    if(!file_exists(str_replace(".src", ".in", $file)))
    {
        $in_file = fopen(str_replace(".src", ".in", $file), "w");
        if($in_file === false)
        {
            exit(11);
        }
        fclose($in_file);
    }

    // Súbor .out
    if(!file_exists(str_replace(".src", ".out", $file)))
    { 
        $out_file = fopen(str_replace(".src", ".out", $file), "w");
        if($out_file === false)
        {
            exit(11);
        }
        fclose($out_file);
    }

    // Súbor .rc
    if(!file_exists(str_replace(".src", ".rc", $file)))
    { 
        $rc_file = fopen(str_replace(".src", ".rc", $file), "w");
        if($rc_file === false)
        {  
            exit(11);
        }
        fwrite($rc_file, "0");  // Zápis do novovytvoreného súboru 
        fclose($rc_file);
    }
}

// Spracovanie argumentov
function parse_args($argc, $argv)
{
    global $args;

    if($argc == 1) return; // Neboli zadané žiadne argumenty
    
    if($argc == 2)
    {
        if($argv[1] == "--help")
        {
            help(); // Výpis nápovedy
            exit(0);
        }    
    }

    // Prechod poľom argumentov
    foreach($argv as $arg)
    {
        if($arg == "test.php")
        {
            continue;
        }
        elseif(substr($arg, 0, 12) == "--directory=") // Testovacia zložka
        {
            $args->directory = substr($arg, 12);
        }            
        elseif($arg == "--recursive") // Rekurzívne testovanie
        {
            $args->recursive = true;
        }            
        elseif(substr($arg, 0, 15) == "--parse-script=") // Cesta ku parse.php
        {
            $args->parse_script = substr($arg, 15);
        }
        elseif(substr($arg, 0, 13) == "--int-script=") // Cesta k interpet.py
        {
            $args->int_script = substr($arg, 13);
        }
        elseif($arg == "--parse-only")  // Testovanie parse.php
        {
            $args->parse_only = true;
        }
        elseif($arg == "--int-only") // Testovanie interpret.py
        {
            $args->int_only = true;
        }
        elseif(substr($arg, 0, 11) == "--jexamxml=") // Cesta k JExamXML
        {
            $args->jexamxml = substr($arg, 11);
        }
        elseif($arg == "--noclean") // priebežné premazávanie pomocných súborov
        {
            $args->noclean = true;
        }
        else
        {
            exit(10); // Neznámy argument
        }
    }
}


// Kontrola správnosti argumentov
function check_arguments()
{
    global $args; 

    // Nesmú sa kombinovať --parse-only a --int-only
    if(
        (isset($args->parse_only) && (isset($args->int_only) || isset($args->int_file))) 
        ||
        (isset($args->int_only) && (isset($args->parse_only) || isset($args->parse_file)))
    )
    {   
  
        exit(10);
    }


    // Implicitná cesta k testovacej zložke (aktuálna zložka)
    if(!isset($args->directory))
    {  
        $args->directory = getcwd();
    }


    // Implicitná cesta k parse.php (hľadá sa "parse.php" v aktuálnej zložke)
    if(!isset($args->parse_script))
    {   
        $args->parse_script = getcwd() . "/parse.php";
    }


    // Implicitná cesta k interpet.py (hľadá sa "interpet.py" v aktuálnej zložke)
    if(!isset($args->int_script))
    {  
        $args->int_script = getcwd() . "/interpret.py";
    }


    // Implicitná cesta k JExamXML (hľadá sa v "/pub/courses/ipp/jexamxml/jexamxml.jar")
    if(!isset($args->jexamxml))
    {  
        $args->jexamxml = "/pub/courses/ipp/jexamxml/jexamxml.jar";
    }

    // Chyby s neexistujúcimi súbormi
    if(
        ((isset($args->parse_only) && !file_exists($args->jexamxml)) // Testy na parse.php vyžadujú JExamXML
        ||
        (!isset($args->parse_only) && !file_exists($args->int_script))) // Testujeme oba (alebo len inetrpet) a interpert.py neexistuje
        ||
        ((!isset($args->int_only) && !file_exists($args->parse_script)) // Testujeme oba (alebo len parser) a parse.php neexistuje
        ||
        (!is_dir($args->directory))) // Zadaná cesta k testovacej zložke nie je zložkou alebo neexistuje

    )
    { 
        exit(41);
    }


}

?>