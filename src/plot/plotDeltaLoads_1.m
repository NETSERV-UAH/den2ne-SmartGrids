%% plotDeltaLoads.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha:  14 Feb 2025

function plotDeltaLoads_1(delta, results_path)

    % Obtenemos los datos del fichero csv indicado
    file_path = fullfile(results_path, strcat("csv/outdata_d", num2str(delta), ".csv"));
    data_table = readtable(file_path, 'NumHeaderLines', 1);
    
    % Pasamos a matriz y filtramos los criterios
    data = data_table{:,:};
    selected_criteria = [1, 3, 4, 5]; % Eliminamos el criterio de distancia
    data = data(selected_criteria, :);
    
    % Balance de potencias
    data_power = data(:, [2 4 6]);
    h=figure();
    set(gcf,'Position',[100 100 900 700]);
    bar(data_power, 0.7, 'grouped', 'FaceColor', 'flat'); % Barras más finas
    grid on
    title("Balance de potencias global - Instante \delta_{" + num2str(delta) + "}")
    ylabel("Potencia (kW)")
    legend("Ideal", "Con pérdidas", "Con pérdidas y capacidades", 'Location', 'southoutside', 'NumColumns', 3)
    set(gca,'XTickLabel', {'Hops', 'Pérdidas', 'Potencia 0', 'Potencia 0 + Pérdidas'});
    print(gcf, fullfile(results_path, strcat('fig/powerBalance_d', num2str(delta))), '-dpdf', '-r0');

    % Flujo absoluto de potencia
    data_power_abs = data(:, [3 5 7]);
    h=figure();
    set(gcf,'Position',[100 100 900 700]);
    bar(data_power_abs, 0.7, 'grouped', 'FaceColor', 'flat'); % Barras más finas
    grid on
    title("Valor absoluto del flujo de potencias - Instante \delta_{" + num2str(delta) + "}")
    ylabel("Potencia (kW)")
    legend("Ideal", "Con pérdidas", "Con pérdidas y capacidades", 'Location', 'southoutside', 'NumColumns', 3)
    set(gca,'XTickLabel', {'Hops', 'Pérdidas', 'Potencia 0', 'Potencia 0 + Pérdidas'});
    print(gcf, fullfile(results_path, strcat('fig/powerAbsFlux_d', num2str(delta))), '-dpdf', '-r0');
    
    % Tiempos extraídos del CSV
    data_timestamps = data(:, [8 9 10]);
    h=figure();
    set(gcf,'Position',[100 100 900 700]);
    bar(data_timestamps, 0.7, 'grouped', 'FaceColor', 'flat'); % Barras más finas
    grid on
    title("Tiempos de cálculo - Instante \delta_{" + num2str(delta) + "}")
    ylabel("Tiempo (ms)")
    legend("Ideal", "Con pérdidas", "Con pérdidas y capacidades", 'Location', 'southoutside', 'NumColumns', 3)
    set(gca,'XTickLabel', {'Hops', 'Pérdidas', 'Potencia 0', 'Potencia 0 + Pérdidas'});
    print(gcf, fullfile(results_path, strcat('fig/timestamps_d', num2str(delta))), '-dpdf', '-r0');
end
